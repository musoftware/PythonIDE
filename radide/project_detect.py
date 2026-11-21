"""Project type detection for File > Open Folder (no Qt; the UI is radide/features/open_detect.py).

``detect(folder)`` scans a folder (bounded depth, heavy/build folders skipped) and returns a
:class:`Detection`: ranked :class:`Candidate` s for the folder itself and, when the folder is not a
project, the projects found in its sub-folders (a repository with ``backend/`` (Laravel) and ``app/``
(Flutter) -> one candidate per sub-folder -> a ``.radsln``).

Each candidate maps the folder to a RAD IDE language plugin id (radide/languages) and project kind,
with everything ``project.radproj`` needs so Run / Debug / IntelliSense / the dynamic project menus
work at once: ``web`` block (root, start page, framework, dev-server command), startup file, modules.
``inplace`` names the foreign format (radide/features/foreign_projects.py) that already opens the folder
natively (Visual Studio .sln, Cargo, VB6 ...): those default to "open in place" (nothing written).

``create_projects(detection, chosen)`` writes ``project.radproj`` (one per project folder) and, for
projects in sub-folders or several projects, ``<Folder>.radsln`` in the opened folder. Existing user
files are never moved or modified; an existing project.radproj / .radsln is kept.

    det = detect(folder)
    det.single()          # the one confident candidate, or None
    det.candidates()      # ranked list (root candidates first, then sub-folder projects)
    created = create_projects(det, [cand, ...])   # -> path to open (folder with .radsln / radproj)
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

IGNORE_DIRS = {"node_modules", "vendor", ".git", ".svn", ".hg", "bin", "obj", "target", ".venv", "venv", "env",
               "build", "dist", "out", "__pycache__", ".idea", ".vscode", ".vs", ".gradle", ".dart_tool",
               ".next", ".nuxt", ".cache", ".tox", ".mypy_cache", ".pytest_cache", "bower_components",
               "Pods", ".radide", ".radide_backup", ".radide_deleted", "_build", "cmake-build-debug",
               "cmake-build-release", ".godot", ".import", "storage", "coverage", "site-packages", "lua_modules",
               "packages", ".angular", ".expo", ".svelte-kit", "tmp", "log", "logs"}
MAX_FILES = 4000             # files looked at per scan
MAX_DEPTH = 3                # loose source files: folder + 3 levels
SUB_DEPTH = 2                # sub-folder projects: children and grandchildren
CONFIDENT = 0.75

# loose source files -> (kind, title, plugin id, main-function regex)
LOOSE = {
    ".py": ("python", "Python program", "python-tk", r"^if\s+__name__\s*==\s*['\"]__main__['\"]"),
    ".cs": ("csharp", "C# sources", "csharp-bridge", r"static\s+(?:async\s+)?(?:void|int|Task)\s+Main\s*\("),
    ".c": ("c", "C program", "c-bridge", r"\bint\s+main\s*\("),
    ".cpp": ("cpp", "C++ program", "cpp-bridge", r"\bint\s+main\s*\("),
    ".cc": ("cpp", "C++ program", "cpp-bridge", r"\bint\s+main\s*\("),
    ".cxx": ("cpp", "C++ program", "cpp-bridge", r"\bint\s+main\s*\("),
    ".java": ("java", "Java sources", "java-bridge", r"static\s+void\s+main\s*\("),
    ".go": ("go", "Go program", "go-bridge", r"^func\s+main\s*\("),
    ".rb": ("ruby", "Ruby scripts", "ruby-bridge", ""),
    ".ring": ("ring", "Ring program", "ring-app", r"^\s*func\s+main\b"),
    ".lua": ("lua", "Lua scripts", "lua-bridge", ""),
    ".pl": ("perl", "Perl scripts", "perl-bridge", ""),
    ".ps1": ("powershell", "PowerShell scripts", "powershell-bridge", ""),
    ".f90": ("fortran", "Fortran program", "fortran-bridge", r"^\s*program\s+\w+"),
    ".f95": ("fortran", "Fortran program", "fortran-bridge", r"^\s*program\s+\w+"),
    ".f": ("fortran", "Fortran program", "fortran-bridge", r"^\s*program\s+\w+"),
    ".dart": ("dart", "Dart program", "dart-bridge", r"\bvoid\s+main\s*\("),
    ".js": ("javascript", "JavaScript files", "javascript", ""),
    ".ts": ("typescript", "TypeScript files", "typescript", ""),
    ".bas": ("vb", "Visual Basic modules", "vb-basic", r"^\s*(?:Public\s+)?Sub\s+Main\b"),
    ".php": ("php", "PHP site", "php-web", ""),
    ".ipynb": ("jupyter", "Jupyter notebooks", "python-tk", ""),
}
# loose files the IDE has no project language for (open in place / plain folder only)
NO_PLUGIN = {".vb": "VB.NET sources (no .vbproj)", ".fs": "F# sources (no .fsproj)", ".fsx": "F# scripts",
             ".kt": "Kotlin sources", ".kts": "Kotlin scripts", ".swift": "Swift sources",
             ".scala": "Scala sources", ".r": "R scripts", ".jl": "Julia scripts", ".zig": "Zig sources",
             ".nim": "Nim sources", ".hs": "Haskell sources", ".ex": "Elixir sources", ".pas": "Pascal sources"}

# foreign formats (radide/foreign/*) for which "open in place" is the natural default
INPLACE_DEFAULT = {"vs", "vs-project", "vb6", "cargo", "cmake", "delphi", "lazarus", "maven", "gradle", "qmake",
                   "vscode", "python-project", "python-requirements", "intellij", "eclipse", "netbeans"}


@dataclass
class Candidate:
    kind: str                        # "laravel", "django", "vite-react", "cargo", "python-tk" ...
    title: str                       # "Laravel site (Laravel 11.x, PHP ^8.2)"
    language: str = ""               # plugin id ("" = no RAD IDE language: in place / plain folder only)
    project_kind: str = "app"        # "app" | "website" | "library"
    folder: Path = Path(".")         # the project folder (the opened folder or a sub-folder)
    confidence: float = 0.9
    evidence: list = field(default_factory=list)
    web: dict | None = None
    startup: str = ""
    modules: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)   # more project.radproj keys
    inplace: str = ""                # foreign format name that opens it natively ("" = none)
    inplace_file: str = ""           # the native project file
    can_create: bool = True
    notes: list = field(default_factory=list)
    forms: list = field(default_factory=list)   # RAD IDE .form files found next to their code (a lost radproj)

    @property
    def default_action(self) -> str:
        """"inplace" (foreign format that opens well natively, nothing written) or "create"."""
        if self.inplace and (not self.can_create or self.extra.get("_prefer_inplace")):
            return "inplace"
        return "create" if self.can_create else ("inplace" if self.inplace else "plain")

    def rel(self, root: Path) -> str:
        try:
            r = Path(self.folder).resolve().relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            return str(self.folder)
        return "." if r in ("", ".") else r

    def label(self, root: Path | None = None) -> str:
        where = self.rel(root) if root is not None else ""
        return f"{self.title}" + (f"  [{where}/]" if where and where != "." else "")

    def radproj(self, name: str = "") -> dict:
        d = {"name": name or Path(self.folder).resolve().name, "language": self.language, "forms": list(self.forms),
             "startup": self.startup, "modules": list(self.modules)}
        if self.project_kind and self.project_kind != "app":
            d["kind"] = self.project_kind
        if self.web is not None:
            d["web"] = dict(self.web)
        for k, v in self.extra.items():
            if not k.startswith("_") and k not in d:
                d[k] = v
        d["detected"] = {"type": self.kind, "title": self.title}
        return d


@dataclass
class Detection:
    root: Path
    here: list = field(default_factory=list)       # candidates for the folder itself (ranked)
    subs: list = field(default_factory=list)       # best candidate of each sub-folder project
    is_rad: bool = False                           # already a RAD IDE project / solution

    def candidates(self) -> list:
        return list(self.here) + list(self.subs)

    def confident(self) -> list:
        return [c for c in self.candidates() if c.confidence >= CONFIDENT]

    def single(self):
        """The candidate to propose alone (one confident project), else None."""
        strong_here = [c for c in self.here if c.confidence >= CONFIDENT]
        if strong_here and not self.subs:
            if len(strong_here) == 1 or strong_here[0].confidence - strong_here[1].confidence >= 0.15:
                return strong_here[0]
            return None
        if not self.here and len(self.subs) == 1:
            return self.subs[0]
        if not strong_here and not self.subs and len(self.here) == 1:
            return self.here[0]
        return None

    def multi(self) -> bool:
        return len(self.subs) >= 2 or (bool(self.subs) and bool(self.here))

    def summary(self) -> str:
        return "; ".join(c.label(self.root) for c in self.candidates()) or "nothing detected"


# =============================================================================== helpers
def _read(p: Path, limit: int = 200_000) -> str:
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except OSError:
        return ""


def _json(p: Path) -> dict:
    try:
        d = json.loads(_read(p))
        return d if isinstance(d, dict) else {}
    except ValueError:
        return {}


def _toml(p: Path) -> dict:
    try:
        import tomllib
        return tomllib.loads(_read(p))
    except Exception:  # noqa: BLE001 - tomllib missing or a broken file
        return {}


def _isf(folder: Path, *names: str) -> bool:
    return any((folder / n).is_file() for n in names)


def _glob1(folder: Path, pattern: str) -> list:
    try:
        return sorted(p for p in folder.glob(pattern) if p.is_file())
    except OSError:
        return []


def walk(folder: Path, max_depth: int = MAX_DEPTH, limit: int = MAX_FILES, keep=()) -> list:
    """Relative posix paths of the files under *folder* (bounded, heavy folders skipped; *keep* = names of
    IGNORE_DIRS that are source folders for this language, e.g. Dart's bin/)."""
    out: list[str] = []
    ignore = IGNORE_DIRS - set(keep)
    root = Path(folder)
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            entries = sorted(os.scandir(d), key=lambda e: e.name.lower())
        except OSError:
            continue
        subdirs = []
        for e in entries:
            try:
                if e.is_dir(follow_symlinks=False):
                    if depth < max_depth and e.name not in ignore and not e.name.startswith("."):
                        subdirs.append(Path(e.path))
                elif e.is_file():
                    out.append(Path(e.path).relative_to(root).as_posix())
                    if len(out) >= limit:
                        return out
            except OSError:
                continue
        stack.extend((s, depth + 1) for s in reversed(subdirs))
    return out


def _composer(folder: Path) -> dict:
    return _json(folder / "composer.json")


def _composer_req(folder: Path) -> dict:
    c = _composer(folder)
    return {**(c.get("require") or {}), **(c.get("require-dev") or {})}


def _lock_version(folder: Path, package: str) -> str:
    lock = _json(folder / "composer.lock")
    for p in (lock.get("packages") or []):
        if isinstance(p, dict) and p.get("name") == package:
            return str(p.get("version") or "").lstrip("v")
    return ""


def _major(v: str) -> str:
    m = re.search(r"(\d+)", v or "")
    return f"{m.group(1)}.x" if m else ""


def _pkg(folder: Path) -> dict:
    return _json(folder / "package.json")


def _deps(pkg: dict) -> dict:
    return {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}


def _py_text_deps(folder: Path) -> str:
    """Lower-case text of the Python dependency files."""
    parts = [_read(folder / n, 60_000) for n in ("requirements.txt", "pyproject.toml", "Pipfile", "setup.py",
                                                 "setup.cfg", "requirements-dev.txt")]
    return "\n".join(parts).lower()


def _first(folder: Path, names) -> str:
    for n in names:
        if (folder / n).is_file():
            return n
    return ""


def _version_of(text: str, rx: str) -> str:
    m = re.search(rx, text or "", re.I | re.M)
    return m.group(1) if m else ""


# =============================================================================== detectors
# Every detector: f(folder) -> list[Candidate] (strong markers only; loose files are handled by _loose)

def _php(folder: Path) -> list:
    req = _composer_req(folder)
    php_req = str(req.get("php") or "")
    php_note = f"PHP {php_req}" if php_req else ""
    out = []
    if (folder / "artisan").is_file() and ("laravel/framework" in req or (folder / "vendor/laravel").is_dir() or
                                           (folder / "bootstrap/app.php").is_file()):
        v = _lock_version(folder, "laravel/framework") or str(req.get("laravel/framework") or "")
        bits = [b for b in (f"Laravel {_major(v)}" if v else "", php_note) if b]
        ev = ["artisan"] + (["composer.json: laravel/framework"] if "laravel/framework" in req else [])
        c = Candidate("laravel", "Laravel site" + (f" ({', '.join(bits)})" if bits else ""), "php-web", "website",
                      folder, 0.97, ev, {"root": "public", "start": "/", "port": 0, "live_reload": True,
                                         "framework": "laravel", "php": "auto"})
        if not (folder / "vendor").is_dir():
            c.notes.append("vendor/ is missing: run Composer > install (or 'composer install') before the first run.")
        out.append(c)
        return out
    if (folder / "spark").is_file() or "codeigniter4/framework" in req or "codeigniter4/appstarter" in \
            str(_composer(folder).get("name") or ""):
        v = _lock_version(folder, "codeigniter4/framework") or str(req.get("codeigniter4/framework") or "")
        bits = [b for b in (f"CodeIgniter {_major(v)}" if v else "CodeIgniter 4", php_note) if b]
        out.append(Candidate("codeigniter", f"CodeIgniter site ({', '.join(bits)})", "php-web", "website", folder,
                             0.95, ["spark" if (folder / "spark").is_file() else "composer.json: codeigniter4"],
                             {"root": "public" if (folder / "public").is_dir() else ".", "start": "", "port": 0,
                              "live_reload": True, "framework": "codeigniter", "php": "auto"}))
        return out
    if "symfony/framework-bundle" in req or ((folder / "bin/console").is_file() and
                                             (folder / "config/bundles.php").is_file()):
        v = _lock_version(folder, "symfony/framework-bundle")
        bits = [b for b in (f"Symfony {_major(v)}" if v else "Symfony", php_note) if b]
        root = "public" if (folder / "public/index.php").is_file() else "."
        out.append(Candidate("symfony", f"Symfony site ({', '.join(bits)})", "php-web", "website", folder, 0.93,
                             ["composer.json: symfony/framework-bundle" if req else "bin/console + config/bundles.php"],
                             {"root": root, "start": "/", "port": 0, "live_reload": True, "router": "index.php",
                              "php": "auto"}))
        return out
    if _isf(folder, "wp-config.php", "wp-config-sample.php") and (folder / "wp-includes").is_dir():
        v = _version_of(_read(folder / "wp-includes/version.php"), r"\$wp_version\s*=\s*'([^']+)'")
        out.append(Candidate("wordpress", "WordPress site" + (f" (WordPress {v})" if v else ""), "php-web", "website",
                             folder, 0.95, ["wp-config.php", "wp-includes/"],
                             {"root": ".", "start": "index.php", "port": 0, "live_reload": True, "php": "auto"}))
        return out
    if "slim/slim" in req or "laminas/laminas-mvc" in req or "cakephp/cakephp" in req or "yiisoft/yii2" in req:
        fw = next(k for k in ("slim/slim", "laminas/laminas-mvc", "cakephp/cakephp", "yiisoft/yii2") if k in req)
        nice = {"slim/slim": "Slim", "laminas/laminas-mvc": "Laminas", "cakephp/cakephp": "CakePHP",
                "yiisoft/yii2": "Yii 2"}[fw]
        root = "public" if (folder / "public/index.php").is_file() else ("webroot" if (folder / "webroot").is_dir()
                                                                           else ("web" if (folder / "web/index.php")
                                                                                 .is_file() else "."))
        out.append(Candidate(nice.lower().replace(" ", ""), f"{nice} site" + (f" ({php_note})" if php_note else ""),
                             "php-web", "website", folder, 0.9, [f"composer.json: {fw}"],
                             {"root": root, "start": "/", "port": 0, "live_reload": True, "router": "index.php",
                              "php": "auto"}))
        return out
    has_index = _isf(folder, "index.php", "public/index.php", "default.php")
    if (folder / "composer.json").is_file() or has_index:
        root = "public" if (folder / "public/index.php").is_file() and not (folder / "index.php").is_file() else "."
        start = "index.php" if _isf(folder / root, "index.php") else ("default.php" if _isf(folder / root, "default.php")
                                                                       else "")
        ev = [x for x in ("composer.json" if (folder / "composer.json").is_file() else "",
                          f"{root}/{start}".replace("./", "") if start else "") if x]
        conf = 0.9 if has_index else 0.7
        if not has_index and not any(folder.glob("*.php")) and not (folder / "src").is_dir():
            conf = 0.55                               # a composer library without a page
        kind_t = "PHP site" if has_index else "PHP project (Composer)"
        out.append(Candidate("php", kind_t + (f" ({php_note})" if php_note else ""), "php-web", "website", folder,
                             conf, ev, {"root": root, "start": start, "port": 0, "live_reload": True, "php": "auto"}))
    return out


def _node(folder: Path) -> list:
    pkg = _pkg(folder)
    if not pkg and not (folder / "package.json").is_file():
        return []
    deps = _deps(pkg)
    scripts = pkg.get("scripts") or {}
    name = str(pkg.get("name") or folder.name)
    node_v = str((pkg.get("engines") or {}).get("node") or "")
    vnote = f", Node {node_v}" if node_v else ""
    ev = ["package.json"]

    def web(**kw):
        d = {"root": ".", "start": "", "port": 0, "live_reload": False, "restart_on_change": False, "timeout": 180}
        d.update(kw)
        return d

    if (folder / "artisan").is_file():
        return []                                      # Laravel's Vite assets: the PHP detector owns the folder
    if "next" in deps:
        return [Candidate("nextjs", f"Next.js app (next {deps['next']}{vnote})", "node-web", "website", folder, 0.95,
                          ev + ["dependency: next"],
                          web(command="npx next dev -p {port} -H 127.0.0.1", framework="nextjs", build="npx next build",
                              dist=".next"))]
    if "nuxt" in deps:
        return [Candidate("nuxt", f"Nuxt app (nuxt {deps['nuxt']})", "node-web", "website", folder, 0.93,
                          ev + ["dependency: nuxt"],
                          web(command="npx nuxi dev --port {port} --host 127.0.0.1", framework="nuxt",
                              build="npx nuxi build", dist=".output"))]
    if "@nestjs/core" in deps:
        main = _first(folder, ("src/main.ts", "src/main.js")) or "src/main.ts"
        return [Candidate("nestjs", f"NestJS app (@nestjs/core {deps['@nestjs/core']}{vnote})", "nestjs-web", "website",
                          folder, 0.96, ev + ["dependency: @nestjs/core"],
                          {"root": ".", "start": main, "port": 0, "live_reload": True})]
    if "@angular/core" in deps:
        ang = _json(folder / "angular.json")
        dist = "dist"
        try:
            proj = next(iter((ang.get("projects") or {}).values()))
            opt = proj["architect"]["build"]["options"]
            dist = str(opt.get("outputPath") or f"dist/{next(iter(ang['projects']))}")
            if isinstance(opt.get("outputPath"), dict):
                dist = str(opt["outputPath"].get("base") or "dist")
            if "browser" in str(proj["architect"]["build"].get("builder", "")) or "application" in \
                    str(proj["architect"]["build"].get("builder", "")):
                dist = dist.rstrip("/") + "/browser"
        except Exception:  # noqa: BLE001 - no / unusual angular.json
            pass
        return [Candidate("angular", f"Angular app (@angular/core {deps['@angular/core']})", "node-web", "website", folder,
                          0.95, ev + ["dependency: @angular/core"] + (["angular.json"] if ang else []),
                          web(command="npx ng serve --port {port} --host 127.0.0.1", framework="angular",
                              build="npx ng build", dist=dist))]
    if "expo" in deps or "react-native" in deps:
        return [Candidate("expo", f"React Native / Expo app (expo {deps.get('expo', '?')})", "node-web", "website",
                          folder, 0.88, ev + ["dependency: expo" if "expo" in deps else "dependency: react-native"],
                          web(command="npx expo start --web --port {port}", framework="expo"),
                          notes=["Runs the Expo web target in the Preview; use Expo Go / an emulator for phones."])]
    if "vite" in deps or _glob1(folder, "vite.config.*"):
        sub = "react-ts" if "react" in deps and "typescript" in deps else \
            "react" if "react" in deps else "vue" if "vue" in deps else "svelte" if "svelte" in deps else "vanilla"
        fid = {"react-ts": "vite-react-ts", "react": "vite-react", "vue": "vite-vue", "svelte": "vite-svelte"}.get(
            sub, "vite-vanilla")
        nice = {"react-ts": "React + TypeScript", "react": "React", "vue": "Vue", "svelte": "Svelte"}.get(sub, "Vite")
        cmd = "npm run dev -- --port {port} --strictPort --host 127.0.0.1" if "dev" in scripts else \
            "npx vite --port {port} --strictPort --host 127.0.0.1"
        return [Candidate(fid, f"{nice} app (Vite {deps.get('vite', '')}".rstrip() + ")", "node-web", "website", folder,
                          0.95, ev + ["dependency: vite"],
                          web(start="index.html" if (folder / "index.html").is_file() else "", command=cmd,
                              framework=fid, build="npm run build" if "build" in scripts else "npx vite build",
                              dist="dist"))]
    if "react-scripts" in deps:
        return [Candidate("cra", "React app (Create React App)", "node-web", "website", folder, 0.93,
                          ev + ["dependency: react-scripts"],
                          web(command="set BROWSER=none&& npm start" if os.name == "nt" else "BROWSER=none npm start",
                              framework="cra", build="npm run build", dist="build"))]
    if "@vue/cli-service" in deps:
        return [Candidate("vue-cli", "Vue app (Vue CLI)", "node-web", "website", folder, 0.93,
                          ev + ["dependency: @vue/cli-service"],
                          web(command="npm run serve -- --port {port} --host 127.0.0.1", framework="vue-cli",
                              build="npm run build", dist="dist"))]
    if "electron" in deps:
        return [Candidate("electron", f"Electron app ({name})", "node-web", "app", folder, 0.85,
                          ev + ["dependency: electron"],
                          web(command="npm start" if "start" in scripts else "npx electron .", framework="electron"),
                          notes=["Electron opens its own window; the Preview stays empty."])]
    servers = [d for d in ("express", "fastify", "koa", "@hapi/hapi", "hono", "restify", "socket.io") if d in deps]
    start = ""
    m = re.match(r"node\s+([\w./-]+\.(?:c|m)?js)", str(scripts.get("start") or ""))
    if m:
        start = m.group(1)
    elif pkg.get("main") and (folder / str(pkg["main"])).is_file():
        start = str(pkg["main"])
    else:
        start = _first(folder, ("server.js", "app.js", "index.js", "main.js", "src/server.js", "src/index.js",
                                "bin/www"))
    if servers or start:
        title = (f"Node.js {servers[0].capitalize() if servers else ''} server".replace("  ", " ") +
                 f" ({start or 'npm start'}{vnote})")
        return [Candidate("express" if "express" in servers else "node", title, "node-web", "website", folder,
                          0.92 if servers else 0.8, ev + [f"dependency: {s}" for s in servers[:2]] +
                          ([f"entry: {start}"] if start else []),
                          {"root": ".", "start": start or "server.js", "port": 0, "live_reload": True})]
    if "start" in scripts or "dev" in scripts:
        cmd = "npm run dev" if "dev" in scripts else "npm start"
        return [Candidate("node", f"Node.js project ({cmd})", "node-web", "website", folder, 0.75, ev,
                          web(command=cmd, live_reload=True))]
    return [Candidate("node", "Node.js package (no server)", "node-web", "website", folder, 0.55, ev,
                      {"root": ".", "start": "", "port": 0, "live_reload": True})]


def _static(folder: Path) -> list:
    start = _first(folder, ("index.html", "index.htm", "default.html", "default.htm"))
    if not start:
        return []
    return [Candidate("static", "Static web site (HTML/CSS/JS)", "static-web", "website", folder, 0.85, [start],
                      {"root": ".", "start": start, "port": 0, "live_reload": True})]


_GUI_RX = {"python-qt": re.compile(r"^\s*(?:from|import)\s+(?:PySide6|PyQt6|PyQt5|PySide2)\b", re.M),
           "python-tk": re.compile(r"^\s*(?:from|import)\s+(?:tkinter|Tkinter|customtkinter|ttkbootstrap)\b", re.M)}
_PYGAME_RX = re.compile(r"^\s*(?:from|import)\s+(?:pygame|arcade|pyglet|ursina)\b", re.M)
_KIVY_RX = re.compile(r"^\s*(?:from|import)\s+kivy\b", re.M)
_MAIN_RX = re.compile(r"^if\s+__name__\s*==\s*['\"]__main__['\"]", re.M)


def _py_files(folder: Path) -> list:
    return [f for f in walk(folder, 2, 1500) if f.endswith(".py")]


def _py_startup(folder: Path, files: list, prefer_rx=None) -> str:
    names = ("main.py", "app.py", "run.py", "game.py", "gui.py", "__main__.py", "program.py", "start.py")
    for n in names:
        if n in files and (prefer_rx is None or prefer_rx.search(_read(folder / n, 40_000))):
            return n[:-3]
    best = ""
    for f in files:
        t = _read(folder / f, 40_000)
        if (prefer_rx is None or prefer_rx.search(t)) and _MAIN_RX.search(t):
            if not best or f.count("/") < best.count("/"):
                best = f
    if best:
        return best[:-3]
    for f in files:
        if prefer_rx is not None and prefer_rx.search(_read(folder / f, 40_000)):
            return f[:-3]
    return ""


def _python(folder: Path) -> list:
    out = []
    deps = _py_text_deps(folder)
    pyver = ""
    pp = _toml(folder / "pyproject.toml") if (folder / "pyproject.toml").is_file() else {}
    if pp:
        pyver = str((pp.get("project") or {}).get("requires-python") or
                    ((pp.get("tool") or {}).get("poetry") or {}).get("dependencies", {}).get("python", "") or "")
    vnote = f", Python {pyver}" if pyver else ""
    if (folder / "manage.py").is_file() and "django" in (_read(folder / "manage.py") + deps).lower():
        from_manage = _version_of(_read(folder / "manage.py"), r"DJANGO_SETTINGS_MODULE['\"]\s*,\s*['\"]([\w.]+)['\"]")
        dv = _version_of(deps, r"django\s*[=~><]=?\s*([\d.]+)")
        out.append(Candidate("django", f"Django site ({('Django ' + dv) if dv else 'Django'}{vnote})", "python-django",
                             "website", folder, 0.97,
                             ["manage.py"] + (["requirements: django"] if "django" in deps else []),
                             {"root": ".", "start": "/", "port": 0, "live_reload": True, "framework": "django",
                              "settings": from_manage or "config.settings"}))
        return out
    files = _py_files(folder)
    if not files and not deps:
        return out
    texts = {f: _read(folder / f, 60_000) for f in files[:200]}
    if "fastapi" in deps or any(re.search(r"\bFastAPI\s*\(", t) for t in texts.values()):
        app = ""
        for rel, target in (("app/main.py", "app.main:app"), ("main.py", "main:app"), ("app.py", "app:app"),
                            ("src/main.py", "src.main:app"), ("api/main.py", "api.main:app")):
            if rel in texts and "FastAPI(" in texts[rel]:
                app = target
                break
        if not app:
            for f, t in texts.items():
                m = re.search(r"^(\w+)\s*=\s*FastAPI\s*\(", t, re.M)
                if m:
                    app = f[:-3].replace("/", ".") + ":" + m.group(1)
                    break
        out.append(Candidate("fastapi", f"FastAPI app ({app or 'app.main:app'}{vnote})", "python-fastapi", "website",
                             folder, 0.94, (["requirements: fastapi"] if "fastapi" in deps else []) +
                             ([f"FastAPI() in {app.split(':')[0]}"] if app else []),
                             {"root": ".", "start": "/", "port": 0, "live_reload": True, "framework": "fastapi",
                              "app": app or "app.main:app"}))
        return out
    if "flask" in deps or any(re.search(r"\bFlask\s*\(\s*__name__", t) for t in texts.values()):
        app = ""
        if (folder / "app/__init__.py").is_file() and "Flask" in texts.get("app/__init__.py", ""):
            app = "app"
        else:
            for n in ("app.py", "wsgi.py", "main.py", "application.py", "server.py", "run.py"):
                if n in texts and "Flask" in texts[n]:
                    app = n[:-3]
                    break
            if not app:
                for f, t in texts.items():
                    if re.search(r"\bFlask\s*\(\s*__name__", t):
                        app = f[:-3].replace("/", ".")
                        break
        out.append(Candidate("flask", f"Flask app ({app or 'app'}{vnote})", "python-flask", "website", folder, 0.93,
                             (["requirements: flask"] if "flask" in deps else []) + ([f"Flask(__name__) in {app}"]
                                                                                     if app else []),
                             {"root": ".", "start": "/", "port": 0, "live_reload": True, "framework": "flask",
                              "app": app or "app"}))
        return out
    mods = [f for f in files]
    nb = [f for f in walk(folder, 2, 1500) if f.endswith(".ipynb")]
    for pid, rx in (("python-qt", _GUI_RX["python-qt"]), ("python-tk", _GUI_RX["python-tk"])):
        hits = [f for f, t in texts.items() if rx.search(t)]
        if hits:
            st = _py_startup(folder, files, rx)
            tk = "Qt (PySide6/PyQt)" if pid == "python-qt" else "Tkinter"
            c = Candidate(pid, f"Python {tk} GUI program ({st or hits[0][:-3]}.py{vnote})", pid, "app", folder, 0.88,
                          [f"{h}: imports {'Qt' if pid == 'python-qt' else 'tkinter'}" for h in hits[:3]],
                          startup=st or hits[0][:-3], modules=mods + nb)
            c.notes.append("Its windows can become designer forms: File > Import > Python GUI program "
                           "(creates a separate RAD project, your files stay unchanged).")
            c.extra["import_gui"] = (st or hits[0][:-3]) + ".py"
            out.append(c)
            return out
    game = [f for f, t in texts.items() if _PYGAME_RX.search(t)]
    if game:
        st = _py_startup(folder, files, _PYGAME_RX) or game[0][:-3]
        has_scenes = bool(_glob1(folder, "*.scene"))
        lib = _version_of("\n".join(texts[g] for g in game[:3]), r"^\s*(?:from|import)\s+(pygame|arcade|pyglet|ursina)")
        out.append(Candidate("pygame", f"Python game ({lib or 'pygame'}, {st}.py)", "pygame" if has_scenes else
                             "python-tk", "app", folder, 0.88, [f"{g}: imports {lib or 'pygame'}" for g in game[:3]],
                             startup=st, modules=mods))
        return out
    kv = [f for f, t in texts.items() if _KIVY_RX.search(t)]
    if kv:
        st = _py_startup(folder, files, _KIVY_RX) or kv[0][:-3]
        out.append(Candidate("kivy", f"Kivy app ({st}.py)", "python-tk", "app", folder, 0.85,
                             [f"{k}: imports kivy" for k in kv[:3]], startup=st, modules=mods))
        return out
    marker = _first(folder, ("pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "requirements.txt"))
    st = _py_startup(folder, files)
    if marker or files:
        conf = 0.85 if marker else (0.7 if st else 0.55)
        title = "Python project" + (f" ({marker}{vnote})" if marker else f" ({len(files)} .py files)")
        c = Candidate("python", title, "python-tk", "app", folder, conf, ([marker] if marker else []) +
                      ([f"entry point: {st}.py"] if st else []), startup=st, modules=mods + nb)
        if not st:
            c.notes.append("No script with if __name__ == '__main__' found: set the startup file in Project Properties.")
        out.append(c)
    return out


def _jupyter(folder: Path) -> list:
    nb = [f for f in walk(folder, 2, 1500) if f.endswith(".ipynb")]
    if not nb:
        return []
    py = _py_files(folder)
    return [Candidate("jupyter", f"Jupyter notebooks ({len(nb)} .ipynb)", "python-tk", "app", folder,
                      0.8 if len(nb) >= len(py) else 0.6, [n for n in nb[:3]],
                      startup=_py_startup(folder, py), modules=nb + py,
                      notes=["Notebooks open in the notebook editor (cells run on the project's Python)."])]


def _dotnet(folder: Path) -> list:
    out = []
    sln = _glob1(folder, "*.sln") + _glob1(folder, "*.slnx")
    projs = _glob1(folder, "*.csproj") + _glob1(folder, "*.vbproj") + _glob1(folder, "*.fsproj") + \
        _glob1(folder, "*.vcxproj")
    if not sln and not projs:
        return out
    if projs and not sln:
        p = projs[0]
        text = _read(p, 40_000)
        tfm = _version_of(text, r"<TargetFrameworks?>([^<]+)<")
        lang = {".csproj": "C#", ".vbproj": "VB.NET", ".fsproj": "F#", ".vcxproj": "C++"}[p.suffix.lower()]
        if lang == "C++" and re.search(r"masm\.(props|targets)|<MASM\s+Include=", text, re.I):
            lang = "C++ / MASM"                         # Visual Studio project with the masm build customization
        web = "Microsoft.NET.Sdk.Web" in text
        winforms = "<UseWindowsForms>true" in text or "<UseWPF>true" in text
        kind_t = ("ASP.NET Core web app" if web else "Windows Forms app" if "<UseWindowsForms>true" in text else
                  "WPF app" if "<UseWPF>true" in text else "console/library project")
        title = f"{lang} {kind_t} ({p.name}" + (f", {tfm}" if tfm else "") + ")"
        if web and p.suffix.lower() == ".csproj":
            c = Candidate("aspnet", title, "aspnet-web", "website", folder, 0.95, [p.name, "Sdk: Microsoft.NET.Sdk.Web"],
                          {"root": ".", "start": "/", "port": 0, "live_reload": True, "framework": "aspnet"},
                          inplace="vs-project", inplace_file=p.name)
            c.notes.append("A project.radproj next to the .csproj: run 'dotnet' commands with the .csproj name "
                           "(dotnet run --project " + p.name + ").")
            c.extra["_prefer_inplace"] = True
            out.append(c)
        else:
            out.append(Candidate("dotnet-" + p.suffix.lower()[1:], title, "", "app", folder, 0.95, [p.name] +
                                 (["Windows Forms designer files"] if winforms else []), inplace="vs-project",
                                 inplace_file=p.name, can_create=False,
                                 notes=["Visual Studio projects open in place: build/run/debug with the .NET SDK, "
                                        "WinForms forms in the designer, nothing written into the folder."]))
        return out
    s = sln[0]
    text = _read(s, 100_000)
    n = len(re.findall(r"^Project\(", text, re.M)) or text.count("<Project ")
    out.append(Candidate("vs-solution", f"Visual Studio solution ({s.name}, {n} project{'s' if n != 1 else ''})", "",
                         "app", folder, 0.97, [s.name], inplace="vs", inplace_file=s.name, can_create=False,
                         notes=["Opens in place: projects, configurations, build/run/debug and WinForms designers."]))
    return out


def _vb6(folder: Path) -> list:
    vbp = _glob1(folder, "*.vbg") + _glob1(folder, "*.vbp")
    if not vbp:
        return []
    return [Candidate("vb6", f"Visual Basic 6 project ({vbp[0].name})", "", "app", folder, 0.97, [vbp[0].name],
                      inplace="vb6", inplace_file=vbp[0].name, can_create=False,
                      notes=["Opens in place: .frm forms in the designer, runs on the built-in VB engine; "
                             "File > Import converts it to a RAD project if you prefer."])]


def _cmake_make(folder: Path) -> list:
    out = []
    if (folder / "CMakeLists.txt").is_file():
        t = _read(folder / "CMakeLists.txt", 40_000)
        name = _version_of(t, r"project\s*\(\s*([\w.-]+)")
        out.append(Candidate("cmake", f"CMake project ({name or 'CMakeLists.txt'})", "", "app", folder, 0.95,
                             ["CMakeLists.txt"], inplace="cmake", inplace_file="CMakeLists.txt", can_create=False,
                             notes=["Opens in place: configure/build with CMake, targets as startup objects, gdb."]))
        return out
    pro = _glob1(folder, "*.pro")
    if pro:
        out.append(Candidate("qmake", f"Qt qmake project ({pro[0].name})", "", "app", folder, 0.93, [pro[0].name],
                             inplace="qmake", inplace_file=pro[0].name, can_create=False))
        return out
    if _isf(folder, "Makefile", "makefile", "GNUmakefile"):
        srcs = [f for f in walk(folder, 2, 1500) if f.lower().endswith((".c", ".cpp", ".cc", ".cxx"))]
        if srcs:
            cpp = any(not s.lower().endswith(".c") for s in srcs)
            pid = "cpp-bridge" if cpp else "c-bridge"
            out.append(Candidate("make-" + ("cpp" if cpp else "c"), f"{'C++' if cpp else 'C'} project (Makefile, "
                                 f"{len(srcs)} source files)", pid, "app", folder, 0.85, ["Makefile"] + srcs[:2],
                                 startup=_main_stem(folder, srcs, r"\bint\s+main\s*\("), modules=srcs,
                                 notes=["Run compiles the sources with the IDE's compiler (gcc / MSVC); "
                                        "your Makefile stays as it is (Terminal: make)."]))
    return out


def _main_stem(folder: Path, files: list, rx: str) -> str:
    if not rx:
        return Path(files[0]).with_suffix("").as_posix() if files else ""
    r = re.compile(rx, re.M | re.I)
    hits = [f for f in files if r.search(_read(folder / f, 60_000))]
    pick = sorted(hits, key=lambda f: (f.count("/"), len(f)))[0] if hits else (files[0] if files else "")
    return Path(pick).with_suffix("").as_posix() if pick else ""


def _rust(folder: Path) -> list:
    if not (folder / "Cargo.toml").is_file():
        return []
    d = _toml(folder / "Cargo.toml")
    pkg = d.get("package") or {}
    ws = d.get("workspace") or {}
    name = str(pkg.get("name") or folder.name)
    ed = str(pkg.get("edition") or "")
    title = (f"Rust Cargo workspace ({len(ws.get('members') or [])} members)" if ws and not pkg else
             f"Rust Cargo crate ({name}" + (f", edition {ed}" if ed else "") + ")")
    c = Candidate("cargo", title, "rust-cargo", "app", folder, 0.97, ["Cargo.toml"], inplace="cargo",
                  inplace_file="Cargo.toml", notes=["Opens in place (rust-analyzer, cargo targets, gdb); "
                                                    "'Create' adds a project.radproj so it can join a RAD solution."])
    c.extra["_prefer_inplace"] = True
    return [c]


def _go(folder: Path) -> list:
    if not (folder / "go.mod").is_file():
        return []
    t = _read(folder / "go.mod")
    mod = _version_of(t, r"^module\s+(\S+)")
    gv = _version_of(t, r"^go\s+([\d.]+)")
    srcs = [f for f in walk(folder, 3, 2000) if f.endswith(".go") and not f.endswith("_test.go")]
    main_files = [f for f in srcs if re.search(r"^package\s+main\b", _read(folder / f, 20_000), re.M)]
    top = [f for f in main_files if "/" not in f] or main_files
    # the Go GUI-Bridge plugin generates its own func main (radmain_gen.go): a module with its own main
    # opens in place (radide/foreign/go_module.py: go run / go test / go build, nothing written)
    return [Candidate("go", f"Go module ({mod or folder.name}" + (f", Go {gv}" if gv else "") + ")", "go-bridge", "app",
                      folder, 0.95, ["go.mod"] + top[:2], inplace="go-module", inplace_file="go.mod", can_create=False,
                      notes=["Opens in place: go run / go test / go build targets, nothing written into the folder."] +
                      ([] if top else ["No package main in the module: a library (Run = go test ./...)."]))]


def _java(folder: Path) -> list:
    out = []
    pom = folder / "pom.xml"
    gradle = _first(folder, ("build.gradle.kts", "build.gradle", "settings.gradle.kts", "settings.gradle"))
    if pom.is_file() or gradle:
        text = _read(pom) if pom.is_file() else _read(folder / gradle)
        kotlin = "kotlin" in text.lower() or any(folder.glob("src/main/kotlin"))
        android = "com.android.application" in text or (folder / "app/src/main/AndroidManifest.xml").is_file()
        spring = "spring-boot" in text
        tool = "Maven" if pom.is_file() else "Gradle"
        lang = "Kotlin" if kotlin else "Java"
        if android:
            out.append(Candidate("android", f"Android app ({tool}, {lang})", "", "app", folder, 0.93, [gradle or "pom.xml"],
                                 inplace="gradle" if gradle else "maven", inplace_file=gradle or "pom.xml",
                                 can_create=False, notes=["Opens in place as a Gradle project (build tasks)."]))
            return out
        if spring:
            c = Candidate("spring", f"Spring Boot app ({tool}, {lang})", "spring-web", "website", folder, 0.93,
                          [gradle or "pom.xml", "spring-boot"], {"root": ".", "start": "/", "port": 0,
                                                                 "live_reload": True, "framework": "spring"},
                          inplace="maven" if pom.is_file() else "gradle", inplace_file="pom.xml" if pom.is_file()
                          else gradle)
            out.append(c)
            return out
        c = Candidate("maven" if pom.is_file() else "gradle", f"{lang} {tool} project", "", "app", folder, 0.95,
                      [gradle or "pom.xml"], inplace="maven" if pom.is_file() else "gradle",
                      inplace_file="pom.xml" if pom.is_file() else gradle, can_create=False,
                      notes=[f"Opens in place: {tool} build/run/test, Swing forms, JDWP debugging."])
        out.append(c)
        return out
    for marker, fmt in ((".project", "eclipse"), ("nbproject/project.xml", "netbeans")):
        if (folder / marker).is_file():
            out.append(Candidate(fmt, f"{fmt.capitalize()} Java project", "", "app", folder, 0.9, [marker],
                                 inplace=fmt, inplace_file=marker, can_create=False))
            return out
    iml = _glob1(folder, "*.iml")
    if iml:
        out.append(Candidate("intellij", f"IntelliJ IDEA module ({iml[0].name})", "", "app", folder, 0.88, [iml[0].name],
                             inplace="intellij", inplace_file=iml[0].name, can_create=False))
    return out


def _ruby(folder: Path) -> list:
    gem = _read(folder / "Gemfile").lower()
    if (folder / "config/application.rb").is_file() or re.search(r"""^\s*gem\s+['"]rails['"]""", gem, re.M):
        rv = _version_of(_read(folder / "Gemfile.lock"), r"^\s{4}rails \(([\d.]+)\)")
        return [Candidate("rails", "Ruby on Rails app" + (f" (Rails {rv})" if rv else ""), "rails-web", "website", folder,
                          0.96, [x for x in ("config/application.rb" if (folder / "config/application.rb").is_file()
                                             else "", "Gemfile: rails" if "rails" in gem else "") if x],
                          {"root": ".", "start": "/", "port": 0, "live_reload": True, "framework": "rails"})]
    if re.search(r"""^\s*gem\s+['"]sinatra['"]""", gem, re.M) or any(
            re.search(r"""require\s+['"]sinatra""", _read(f, 20_000)) for f in _glob1(folder, "*.rb")[:20]):
        return [Candidate("sinatra", "Sinatra app (Ruby)", "rails-web", "website", folder, 0.9,
                          ["Gemfile: sinatra" if "sinatra" in gem else "require 'sinatra'"],
                          {"root": ".", "start": "/", "port": 0, "live_reload": True, "framework": "sinatra"})]
    if (folder / "Gemfile").is_file():
        rbs = [f for f in walk(folder, 2, 1500) if f.endswith(".rb")]
        c = Candidate("ruby", "Ruby project (Gemfile)", "ruby-bridge", "app", folder, 0.8, ["Gemfile"],
                      startup=_main_stem(folder, [f for f in rbs if "/" not in f] or rbs, ""), modules=rbs,
                      inplace="loose", notes=["Opens in place: each script runs with ruby (bundle install first)."])
        c.extra["_prefer_inplace"] = True
        return [c]
    return []


def _dart(folder: Path) -> list:
    if not (folder / "pubspec.yaml").is_file():
        return []
    t = _read(folder / "pubspec.yaml")
    name = _version_of(t, r"^name:\s*([\w-]+)")
    if re.search(r"^\s+flutter:\s*\n\s+sdk:\s*flutter", t, re.M) or re.search(r"sdk:\s*flutter", t):
        main = "lib/main.dart" if (folder / "lib/main.dart").is_file() else ""
        c = Candidate("flutter", f"Flutter app ({name or folder.name})", "flutter", "app", folder, 0.96,
                      ["pubspec.yaml: sdk flutter"] + ([main] if main else []),
                      modules=[f for f in walk(folder / "lib", 3, 1500) if f.endswith(".dart")])
        c.modules = ["lib/" + m for m in c.modules] + ["pubspec.yaml"]
        c.extra["native_app"] = True                # its own lib/main.dart: the IDE generates nothing
        c.notes.append("Your lib/main.dart stays yours: Run = flutter run (devices, hot reload).")
        return [c]
    srcs = [f for f in walk(folder, 3, 1500, keep=("bin",)) if f.endswith(".dart")]
    bin_ = [f for f in srcs if f.startswith("bin/")] or srcs
    c = Candidate("dart", f"Dart package ({name or folder.name})", "dart-bridge", "app", folder, 0.9,
                  ["pubspec.yaml"], startup=_main_stem(folder, bin_, r"\bvoid\s+main\s*\("), modules=srcs,
                  inplace="loose", notes=["Opens in place: dart run <program> for each program with main()."])
    c.extra["_prefer_inplace"] = True
    return [c]


def _godot(folder: Path) -> list:
    if not (folder / "project.godot").is_file():
        return []
    t = _read(folder / "project.godot")
    name = _version_of(t, r'^config/name\s*=\s*"([^"]*)"')
    feat = _version_of(t, r'config/features\s*=\s*PackedStringArray\("([\d.]+)"')
    c = Candidate("godot", f"Godot game ({name or folder.name}" + (f", Godot {feat}" if feat else "") + ")", "godot",
                  "app", folder, 0.96, ["project.godot"],
                  modules=[f for f in walk(folder, 3, 2000) if f.endswith((".gd", ".cs", ".tscn", ".gdshader"))][:500])
    c.extra["native_app"] = True                    # scenes stay Godot's own (.tscn); Run = godot --path
    if not _glob1(folder, "*.scene"):
        c.notes.append("Run starts Godot on your project (godot --path); your .tscn scenes are not touched.")
    return [c]


def _pascal(folder: Path) -> list:
    d = _glob1(folder, "*.groupproj") + _glob1(folder, "*.dproj") + _glob1(folder, "*.dpr") + _glob1(folder, "*.dpk")
    if d:
        return [Candidate("delphi", f"Delphi project ({d[0].name})", "", "app", folder, 0.95, [d[0].name],
                          inplace="delphi", inplace_file=d[0].name, can_create=False,
                          notes=["Opens in place: .dfm forms in the designer, builds with Free Pascal / Delphi."])]
    lz = _glob1(folder, "*.lpi") + _glob1(folder, "*.lpr")
    if lz:
        return [Candidate("lazarus", f"Lazarus project ({lz[0].name})", "", "app", folder, 0.95, [lz[0].name],
                          inplace="lazarus", inplace_file=lz[0].name, can_create=False)]
    return []


def _vscode(folder: Path) -> list:
    ws = _glob1(folder, "*.code-workspace")
    if ws:
        return [Candidate("vscode-workspace", f"VS Code workspace ({ws[0].name})", "", "app", folder, 0.8, [ws[0].name],
                          inplace="vscode", inplace_file=ws[0].name, can_create=False)]
    return []


def _ring(folder: Path) -> list:
    rings = [f for f in walk(folder, 2, 1500) if f.endswith(".ring")]
    if not rings:
        return []
    qt = any(re.search(r'load\s+["\']guilib\.ring', _read(folder / f, 20_000), re.I) for f in rings[:30])
    st = _main_stem(folder, [f for f in rings if "/" not in f] or rings, r"^\s*func\s+main\b")
    for n in ("main", "start", "app"):
        if f"{n}.ring" in rings:
            st = n
    return [Candidate("ring", f"Ring {'GUI (RingQt) ' if qt else ''}program ({len(rings)} .ring files)", "ring-app",
                      "app", folder, 0.85, rings[:3], startup=st, modules=rings[:500])]


def _asm(folder: Path) -> list:
    """Assembly sources (.asm / .s / .nasm, RadASM .rap, WinAsm .wap): dialect guessed per program
    (radide/foreign/asm_folder.py); opens in place, 8086 / DOS programs in the teaching emulator."""
    files = walk(folder, 2, 1500)
    srcs = [f for f in files if f.lower().endswith((".asm", ".s", ".nasm", ".fasm", ".masm"))]
    ide = [f for f in files if "/" not in f and f.lower().endswith((".rap", ".wap"))]
    if not srcs and not ide:
        return []
    from .foreign.asm_folder import DIALECT_TITLES, PLUGIN_IDS, plugin_for_dialect, scan_folder
    info = scan_folder(folder, [f for f in files if f.lower().endswith((".asm", ".s", ".nasm", ".fasm", ".masm",
                                                                        ".inc", ".mac"))][:600])
    others = [f for f in files if f.lower().endswith((".c", ".cpp", ".cc", ".rs", ".go", ".cs", ".pas", ".dpr"))]
    d = info.dialect
    where = f"{len(info.sources)} source{'s' if len(info.sources) != 1 else ''}"
    if ide:
        title = f"{'RadASM' if ide[0].lower().endswith('.rap') else 'WinAsm Studio'} project ({ide[0]}, {where})"
    else:
        title = f"Assembly program ({info.title()}, {where}" + \
            (f", entry {info.programs[0].file}" if info.programs else "") + ")"
    conf = 0.9 if ide else (0.85 if info.programs and len(srcs) >= len(others) else 0.55)
    pid = plugin_for_dialect(d)
    c = Candidate("asm", title, pid, "app", folder, conf, (ide or []) + srcs[:3],
                  startup=Path(info.programs[0].file).with_suffix("").as_posix() if info.programs else "",
                  modules=info.sources + info.includes, inplace="loose",
                  inplace_file=ide[0] if ide else "",
                  can_create=bool(pid) and pid == PLUGIN_IDS.get(d) and not ide)
    c.extra["_prefer_inplace"] = True
    c.extra["_asm_dialect"] = d
    main = next((p for p in info.programs if p.dialect == d), None)
    if main is not None and d != "8086":       # radide/asm/build.py settings of a created project.radproj
        c.extra["asm"] = {"assembler": d, "arch": "x86" if main.bits == 32 else "x64", "entry": main.entry}
    c.notes.append(f"Dialect: {DIALECT_TITLES.get(d, d)} (guessed from the code).")
    c.notes.append("Opens in place: each program with an entry point is a run target, built in the IDE state folder.")
    if "8086" in info.dialects:
        c.notes.append("8086 / DOS programs run in the 8086 emulator.")
    if any(p.sasm for p in info.programs):
        c.notes.append("SASM programs (%include \"io64.inc\"): SASM's include folder is used when SASM is installed.")
    return [c]


DETECTORS = [_dotnet, _vb6, _pascal, _rust, _go, _java, _godot, _dart, _ruby, _php, _python, _node, _cmake_make,
             _vscode, _ring, _asm, _jupyter, _static]


# =============================================================================== loose files
def _loose(folder: Path, exclude_kinds: set) -> list:
    files = walk(folder, MAX_DEPTH)
    counts: dict[str, list] = {}
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in LOOSE or ext in NO_PLUGIN or ext in (".frm", ".hpp", ".h"):
            counts.setdefault(ext, []).append(f)
    out = []
    groups: dict[str, list] = {}
    for ext, fl in counts.items():
        if ext in LOOSE:
            kind = LOOSE[ext][0]
            if kind in exclude_kinds or kind in ("python", "jupyter", "ring"):
                continue                        # handled by the dedicated detectors
            groups.setdefault(kind, []).extend(fl)
    if "c" in groups and "cpp" in groups:     # C and C++ mixed: a C++ project compiles both
        groups["cpp"] += groups.pop("c")
    for kind, fl in groups.items():
        ext0 = next(e for e, v in LOOSE.items() if v[0] == kind)
        _k, title, pid, rx = LOOSE[ext0]
        fl = sorted(set(fl), key=lambda f: (f.count("/"), f.lower()))
        if kind == "javascript" and any(f.endswith(".ts") for f in fl):
            continue
        if kind in ("javascript", "typescript") and (folder / "index.html").is_file():
            continue                          # scripts of a static site
        if kind == "php":
            continue                          # PHP: _php sees index.php / composer.json
        if kind == "vb":
            # VB6 sources without a .vbp: .bas modules run on the built-in VB engine
            frms = counts.get(".frm", [])
            st = _main_stem(folder, fl, rx)
            c = Candidate("vb", f"Visual Basic modules ({len(fl)} .bas" + (f", {len(frms)} .frm" if frms else "") + ")",
                          pid, "app", folder, 0.65, fl[:3], startup=st, modules=fl[:300])
            if frms:
                c.notes.append(".frm forms without a .vbp: use File > Import > VB6 project to convert them.")
            out.append(c)
            continue
        st = _main_stem(folder, fl, rx)
        has_main = bool(rx) and any(re.search(rx, _read(folder / f, 60_000), re.M | re.I) for f in fl[:60])
        conf = 0.7 if has_main else 0.6
        if kind in ("c", "cpp"):
            fl = [f for f in fl if not f.lower().endswith((".h", ".hpp"))]
        if not fl:
            continue
        c = Candidate(kind, f"{title} ({len(fl)} file{'s' if len(fl) != 1 else ''}"
                            + (f", entry {Path(st).name}" if st else "") + ")", pid, "app", folder, conf,
                      fl[:3], startup=st, modules=fl[:500])
        if kind in ("csharp", "java", "go") and has_main:
            # the RAD bridge plugins generate their own entry point: programs with their own Main/main open
            # in place (radide/foreign/loose_sources.py builds them in the IDE state folder)
            c.inplace, c.can_create = "loose", False
            c.notes.append("Programs with their own " + ("Main" if kind == "csharp" else "main") + " open in place: "
                           "built and run from the IDE state folder (dotnet / javac / go run), nothing written here.")
        if kind in ("lua", "perl", "ruby", "powershell", "dart"):
            # the GUI-Bridge plugins run forms; plain scripts run in place with their interpreter
            # (radide/foreign/loose_sources.py); "Create" stays available for adding RAD forms later
            c.inplace = "loose"
            c.extra["_prefer_inplace"] = True
            c.notes.append("Scripts open in place: each script is a run target (its own interpreter), nothing "
                           "written here. 'Create' makes a RAD GUI-Bridge project for adding forms.")
        out.append(c)
    for ext, fl in counts.items():
        if ext in NO_PLUGIN and len(fl) >= 1:
            out.append(Candidate("other" + ext, f"{NO_PLUGIN[ext]} ({len(fl)} files)", "", "app", folder, 0.4, fl[:3],
                                 can_create=False,
                                 notes=["RAD IDE has no project language for these files: open the folder as a plain "
                                        "folder workspace (editor, terminal, Git, VS Code tasks)."]))
    return out


# =============================================================================== API
def is_rad_folder(folder: Path) -> bool:
    folder = Path(folder)
    try:
        return (folder / "project.radproj").is_file() or any(folder.glob("*.radsln"))
    except OSError:
        return False


def detect_here(folder: Path, loose: bool = True) -> list:
    """Ranked candidates for exactly this folder (strong markers first; loose sources when *loose*)."""
    folder = Path(folder)
    out: list[Candidate] = []
    for det in DETECTORS:
        try:
            out += det(folder)
        except Exception as e:  # noqa: BLE001 - one broken detector must not hide the others
            out.append(Candidate("error", f"detector {det.__name__} failed: {e}", confidence=0.0, can_create=False,
                                 folder=folder))
    out = [c for c in out if c.kind != "error"]
    out = _dedupe(folder, out)
    if loose:
        have = {c.kind for c in out}
        if not any(c.confidence >= CONFIDENT for c in out):
            have |= {"c", "cpp"} if any(c.kind.startswith("make-") for c in out) else set()
            out += _loose(folder, have)
    for c in out:
        c.folder = folder
        _attach_inplace(c)
        _attach_forms(c)
    out.sort(key=lambda c: -c.confidence)
    return out


def _dedupe(folder: Path, cands: list) -> list:
    """Drop candidates explained by a stronger one (Laravel's package.json, a site's index.html ...)."""
    kinds = {c.kind for c in cands}
    web_backends = {"laravel", "codeigniter", "symfony", "wordpress", "django", "flask", "fastapi", "rails",
                    "sinatra", "nestjs", "nextjs", "nuxt", "angular", "express", "aspnet", "spring", "cra",
                    "vue-cli", "php", "slim", "laminas", "cakephp", "yii2"} | {k for k in kinds if k.startswith("vite")}
    out = []
    for c in cands:
        if c.kind == "static" and (kinds & web_backends or "node" in kinds or "flutter" in kinds or "godot" in kinds):
            continue                          # index.html of a framework app / web build
        if c.kind == "node" and kinds & ({"laravel", "codeigniter", "symfony", "rails", "django", "flask", "aspnet",
                                          "spring", "php", "wordpress"}):
            continue                          # front-end tooling of a backend
        if c.kind == "jupyter" and kinds & {"django", "flask", "fastapi", "python-tk", "python-qt", "pygame",
                                            "python", "kivy"}:
            continue
        if c.kind == "python" and c.confidence < CONFIDENT and kinds & (web_backends | {"godot", "cargo", "go"}):
            continue                          # helper scripts of another project
        if c.kind == "ring" and kinds - {"ring", "static"}:
            c.confidence = min(c.confidence, 0.6)
        if c.kind == "asm" and kinds - {"asm", "static", "vscode-workspace"} and not c.inplace_file:
            c.confidence = min(c.confidence, 0.5)    # .asm / .s helpers of a C / Rust / CMake ... project
        if c.kind == "vscode-workspace" and len(kinds) > 1:
            c.confidence = 0.5
        if c.kind in ("intellij", "eclipse", "netbeans", "vscode-workspace") and any(
                o.confidence >= 0.9 and o.language for o in cands if o is not c):
            continue                          # IDE metadata of a Flutter / Python ... project
        if c.kind == "php" and kinds & {"nextjs", "nuxt", "angular", "nestjs"} | {k for k in kinds if
                                                                                    k.startswith("vite")}:
            c.confidence = min(c.confidence, 0.6)
        out.append(c)
    return out


def _attach_inplace(c: Candidate) -> None:
    """Fill ``inplace`` for candidates whose folder a registered foreign format also opens."""
    if c.inplace:
        return
    try:
        from .features.foreign_projects import probe_folder
        hit = probe_folder(c.folder)
    except Exception:  # noqa: BLE001
        hit = None
    if hit:
        fmt, path = hit
        c.inplace, c.inplace_file = fmt.name, Path(path).name
        if fmt.name in ("python-project", "python-requirements") and c.kind == "python":
            c.extra["_prefer_inplace"] = True


def _attach_forms(c: Candidate) -> None:
    """RAD IDE .form files with their code file next to them (a project whose project.radproj was lost
    or a copied folder): they become the project's forms again (startup = the first one)."""
    if not c.language or c.project_kind == "website" or c.kind in ("godot", "flutter"):
        return
    try:
        from .languages import get_plugin
        plugin = get_plugin(c.language)
    except Exception:  # noqa: BLE001
        return
    forms = []
    for f in _glob1(Path(c.folder), "*.form"):
        if (Path(c.folder) / plugin.code_file(f.stem)).is_file():
            forms.append(f.stem)
    if not forms:
        return
    c.forms = forms
    own = {plugin.code_file(n) for n in forms} | {plugin.designer_file(n) for n in forms}
    c.modules = [m for m in c.modules if m not in own]
    if c.startup not in forms:
        c.startup = forms[0]
    c.evidence.append(f"{len(forms)} RAD IDE form{'s' if len(forms) != 1 else ''} ({', '.join(forms[:3])})")
    c.confidence = max(c.confidence, 0.9)


def _child_dirs(root: Path, depth: int) -> list:
    out = []
    try:
        kids = sorted((Path(e.path) for e in os.scandir(root) if e.is_dir(follow_symlinks=False)
                       and e.name not in IGNORE_DIRS and not e.name.startswith(".")), key=lambda p: p.name.lower())
    except OSError:
        return out
    for k in kids[:200]:
        out.append((k, 1))
    return out


def detect(folder, sub_depth: int = SUB_DEPTH) -> Detection:
    """Detect the project type(s) of *folder* (see the module doc)."""
    root = Path(folder).resolve()
    det = Detection(root)
    det.is_rad = is_rad_folder(root)
    det.here = detect_here(root)
    strong = [c for c in det.here if c.confidence >= CONFIDENT]
    if strong:
        return det
    subs: list[Candidate] = []

    def visit(d: Path, depth: int):
        if is_rad_folder(d):
            return
        cands = [c for c in detect_here(d, loose=False) if c.confidence >= CONFIDENT]
        if cands:
            subs.append(cands[0])
            return
        if depth < sub_depth:
            for k, _ in _child_dirs(d, 1):
                visit(k, depth + 1)
    for k, _ in _child_dirs(root, 1):
        visit(k, 1)
    det.subs = subs
    if subs:                                   # loose files at the root of a multi-project folder: weak extras
        prefixes = tuple(s.rel(root) + "/" for s in subs)

        def own(c):                            # files of the root candidate outside the sub-projects
            files = c.modules or c.evidence
            return any(not str(f).startswith(prefixes) for f in files)
        det.here = [c for c in det.here if c.confidence >= 0.6 and c.can_create and c.kind not in
                    ("javascript", "typescript") and own(c)]
    return det


# =============================================================================== create
def unique_names(cands: list, root: Path) -> list:
    names, out = set(), []
    for c in cands:
        base = re.sub(r"[^\w.-]+", "_", Path(c.folder).resolve().name) or "Project"
        n, i = base, 2
        while n.lower() in names:
            n = f"{base}{i}"
            i += 1
        names.add(n.lower())
        out.append(n)
    return out


def write_radproj(cand: Candidate, name: str = "") -> Path:
    """Write project.radproj for *cand* (an existing one is kept). Returns its path."""
    folder = Path(cand.folder)
    target = folder / "project.radproj"
    if target.exists():
        return target
    if not cand.language:
        raise ValueError(f"{cand.title}: RAD IDE has no project language for it")
    data = cand.radproj(name)
    if cand.language == "rust-cargo":                     # cargo targets / files like New Project > Rust
        try:
            from .languages.rust_cargo import RustCargoPlugin, _adapter
            from .model import Project
            p = Project(folder, data["name"], "rust-cargo")
            RustCargoPlugin.refresh_modules(p)
            data["modules"] = p.modules
            targets = _adapter(folder).targets
            data["startup"] = targets[0].name if targets else ""
        except Exception:  # noqa: BLE001 - keep the plain file list
            pass
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def create_projects(det: Detection, chosen: list, solution_name: str = "") -> Path:
    """Write the project files for the *chosen* candidates; returns what to open (a folder).

    One candidate in the opened folder itself -> project.radproj there. Otherwise (a project in a
    sub-folder, or several projects) -> project.radproj in each project folder + ``<Folder>.radsln``
    in the opened folder (startup = the first chosen project)."""
    root = Path(det.root)
    chosen = [c for c in chosen if c.can_create and c.language]
    if not chosen:
        raise ValueError("nothing to create")
    seen, uniq = set(), []
    for c in chosen:                       # one project per folder
        key = os.path.normcase(str(Path(c.folder).resolve()))
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    chosen = uniq
    names = unique_names(chosen, root)
    if len(chosen) == 1 and Path(chosen[0].folder).resolve() == root:
        write_radproj(chosen[0], names[0])
        return root
    from .solution import Solution, SolutionProject
    entries = []
    for c, n in zip(chosen, names):
        write_radproj(c, n)
        try:
            n = json.loads((Path(c.folder) / "project.radproj").read_text(encoding="utf-8")).get("name") or n
        except (OSError, ValueError):
            pass
        entries.append(SolutionProject(str(n), c.rel(root)))
    sname = solution_name or re.sub(r"[^\w.-]+", "_", root.name) or "Solution"
    existing = sorted(root.glob("*.radsln"))
    if existing:
        return root
    Solution(sname, root, entries, entries[0].name, None).save(root / f"{sname}.radsln")
    return root


__all__ = ["Candidate", "Detection", "detect", "detect_here", "create_projects", "write_radproj", "walk",
           "is_rad_folder", "IGNORE_DIRS", "CONFIDENT"]
