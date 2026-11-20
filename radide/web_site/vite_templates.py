"""Front-end framework projects: React, Vue, Svelte (Vite) and Angular (Angular CLI).

New Project > Web (or the App Gallery) creates them with the frameworks' own official generators:

- ``npm create vite@latest . -- --template <react|react-ts|vue|vue-ts|svelte|svelte-ts|vanilla> --no-interactive``
- ``npx -y @angular/cli@latest new <name> --directory . --defaults --skip-git --ssr=false --interactive=false``

then ``npm install``. The project is a ``node-web`` site whose ``web`` block says how to run it:
``command`` = ``npm run dev -- --port {port} --strictPort --host 127.0.0.1`` (``ng serve`` for Angular) behind
the IDE's DevServer (Requests dock, Preview; the framework's own hot reload / HMR WebSocket passes through),
``live_reload`` / ``restart_on_change`` = False (the framework reloads itself), ``framework`` = the template id
(F5 then debugs the app's JavaScript in the Preview, with source maps back to ``src/*.jsx|vue|svelte|ts``),
``build`` = ``npm run build`` and ``dist`` = the output folder (Site > Build / Preview Production Build).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ANGULAR_FALLBACK = "20"           # Angular CLI major for Node.js 20.19+ / 22.12+ (tested with Node 22.22)
DEV_COMMAND = "npm run dev -- --port {port} --strictPort --host 127.0.0.1"


@dataclass(frozen=True)
class Framework:
    id: str
    title: str
    description: str
    vite_template: str = ""          # create-vite --template value ("" = Angular CLI)
    main_file: str = "src/main.js"   # opened after creation
    dist: str = "dist"
    command: str = DEV_COMMAND
    build: str = "npm run build"


FRAMEWORKS: list[Framework] = [
    Framework("vite-react", "React (Vite)",
              "React 19 single-page app created with 'npm create vite' (template react): JSX components, "
              "hot module replacement, 'npm run build' to dist/.", "react", "src/App.jsx"),
    Framework("vite-react-ts", "React + TypeScript (Vite)",
              "React with TypeScript (template react-ts): .tsx components, type checking in the editor.",
              "react-ts", "src/App.tsx"),
    Framework("vite-vue", "Vue (Vite)",
              "Vue 3 single-page app created with 'npm create vite' (template vue): single-file components "
              "(.vue), hot reload, 'npm run build'.", "vue", "src/App.vue"),
    Framework("vite-svelte", "Svelte (Vite)",
              "Svelte 5 app created with 'npm create vite' (template svelte): .svelte components, hot reload.",
              "svelte", "src/App.svelte"),
    Framework("vite-vanilla", "Vanilla JavaScript (Vite)",
              "Plain JavaScript with the Vite dev server and bundler (template vanilla): ES modules, CSS imports, "
              "hot reload, 'npm run build'.", "vanilla", "src/main.js"),
    Framework("angular", "Angular",
              "Angular app created with the official Angular CLI ('ng new --defaults', no SSR): components, "
              "'ng serve' with live reload, 'ng build' to dist/. The first creation downloads the CLI (~1 min).",
              "", "src/app/app.ts", "dist",
              "npx ng serve --port {port} --host 127.0.0.1", "npx ng build"),
]


def get_framework(fid: str) -> Framework | None:
    return next((f for f in FRAMEWORKS if f.id == fid), None)


def npm_exe() -> str:
    return shutil.which("npm") or shutil.which("npm.cmd") or ""


def npx_exe() -> str:
    return shutil.which("npx") or shutil.which("npx.cmd") or ""


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9-]+", "-", name.strip().lower()).strip("-")
    return s if s and s[0].isalpha() else ("app-" + s if s else "app")


def run(argv: list[str], cwd: Path, log, timeout: int = 900) -> None:
    """Run a tool, streaming its output to *log*; raises RuntimeError on failure."""
    log("> " + " ".join(argv))
    try:
        p = subprocess.Popen(argv, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    except OSError as e:
        raise RuntimeError(f"cannot run {argv[0]}: {e}") from e
    ansi = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
    tail: list[str] = []
    try:
        for raw in iter(p.stdout.readline, b""):
            line = ansi.sub("", raw.decode("utf-8", "replace")).rstrip()
            if line.strip():
                tail = (tail + [line])[-6:]
                try:
                    log(line)
                except Exception:  # noqa: BLE001 - a console that cannot print "◇" must not stop npm
                    pass
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        raise RuntimeError(f"{Path(argv[0]).name} did not finish in {timeout} s")
    if p.returncode:
        raise RuntimeError(f"{Path(argv[0]).name} {' '.join(argv[1:3])} failed (exit code {p.returncode}): " +
                           " / ".join(tail[-3:]))


def web_block(fw: Framework) -> dict:
    return {"root": ".", "start": "index.html" if fw.vite_template else "", "command": fw.command,
            "live_reload": False, "restart_on_change": False, "framework": fw.id, "build": fw.build,
            "dist": fw.dist, "timeout": 180}


def create(fid: str, folder: Path, name: str, log=None, install: bool = True) -> dict:
    """Create a framework project in *folder* (empty or holding only IDE files); returns the ``web`` block."""
    fw = get_framework(fid)
    if fw is None:
        raise KeyError(f"unknown framework template {fid!r}")
    log = log or (lambda _s: None)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    npm, npx = npm_exe(), npx_exe()
    if not npm or not npx:
        raise RuntimeError("Node.js (npm / npx) is needed - install it from https://nodejs.org")
    busy = [p.name for p in folder.iterdir() if p.name not in ("project.radproj", ".radide")]
    if busy:
        raise RuntimeError(f"the folder is not empty ({', '.join(busy[:5])})")
    if fw.vite_template:
        run([npm, "create", "vite@latest", ".", "--", "--template", fw.vite_template, "--no-interactive"],
            folder, log, 600)
        pkg = folder / "package.json"
        try:                                   # create-vite names the package after the folder
            data = json.loads(pkg.read_text(encoding="utf-8"))
            data["name"] = slug(name)
            pkg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        except (OSError, ValueError):
            pass
    else:
        args = ["new", slug(name), "--directory", ".", "--defaults", "--skip-git", "--skip-install", "--ssr=false",
                "--style=css", "--interactive=false"]
        try:
            run([npx, "-y", "@angular/cli@latest", *args], folder, log, 900)
        except RuntimeError as e:              # the newest CLI wants a newer Node.js: use the last that fits
            if "Node.js version" not in str(e):
                raise
            log(f"The latest Angular CLI needs a newer Node.js - using @angular/cli@{ANGULAR_FALLBACK}")
            run([npx, "-y", f"@angular/cli@{ANGULAR_FALLBACK}", *args], folder, log, 900)
        dist = _angular_dist(folder)
        if dist:
            fw = Framework(**{**fw.__dict__, "dist": dist})
    if not (folder / "package.json").is_file():
        raise RuntimeError("the generator did not create package.json")
    if install:
        run([npm, "install", "--no-audit", "--no-fund"], folder, log, 1200)
    return web_block(fw)


def _angular_dist(folder: Path) -> str:
    try:
        data = json.loads((folder / "angular.json").read_text(encoding="utf-8"))
        for proj in (data.get("projects") or {}).values():
            out = (((proj.get("architect") or {}).get("build") or {}).get("options") or {}).get("outputPath")
            if isinstance(out, str):
                return out + "/browser"
            if isinstance(out, dict) and out.get("base"):
                return out["base"] + "/browser"
            name = next(iter(data["projects"]))
            return f"dist/{name}/browser"
    except (OSError, ValueError, StopIteration, KeyError):
        pass
    return "dist"


def build_command(project) -> str:
    from .project import web_config
    cfg = web_config(project)
    if cfg.get("build"):
        return str(cfg["build"])
    try:
        data = json.loads((Path(project.folder) / "package.json").read_text(encoding="utf-8"))
        if "build" in (data.get("scripts") or {}):
            return "npm run build"
    except (OSError, ValueError):
        pass
    return ""


def register(progress=None) -> None:
    """Add the frameworks to the New Project dialog's Node.js templates (web_site.project registry).
    *progress(title, fn)* runs fn(log) with a progress window (the IDE passes app_gallery.run_with_progress)."""
    from .project import SiteTemplate, register_template

    for i, fw in enumerate(FRAMEWORKS):
        def make(folder, name, _fw=fw):
            if progress is None:
                return create(_fw.id, folder, name)
            return progress(f"Creating {_fw.title} project", lambda log: create(_fw.id, folder, name, log))
        register_template(SiteTemplate(fw.id, fw.title, fw.description, ("node-web",), make, order=200 + i,
                                       icon="SP_FileDialogContentsView",
                                       extra={"category": "Front-end frameworks", "needs": ["node", "npm",
                                                                                             "internet"],
                                              "heavy": True, "framework": True, "main": fw.main_file}))


__all__ = ["FRAMEWORKS", "Framework", "build_command", "create", "get_framework", "register", "web_block"]
