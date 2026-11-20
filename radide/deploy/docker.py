"""Docker support for RAD IDE projects (no Qt in this module).

* CLI detection: docker / podman (+ "docker compose", "docker-compose", "podman compose"). Nothing is installed:
  Docker Desktop needs admin rights, so the IDE only uses a CLI that is already there.
* Stack detection: what kind of project a folder is (Django, Flask, FastAPI, Node / Express, Next.js, NestJS,
  Vite / React static build, PHP, Laravel, CodeIgniter, static HTML, ASP.NET, Spring (Maven / Gradle), Rails, Go).
  Desktop projects (python-tk, PySide6, Kivy, pygame, VB6 ...) are reported as "desktop" and skipped.
* Generators: Dockerfile, .dockerignore, compose.yaml (optional database / cache service, compose "watch"),
  .devcontainer/devcontainer.json.
* Lint: a built-in Dockerfile checker, hadolint (downloaded on demand into %LOCALAPPDATA%\\RADIDE\\tools\\hadolint,
  sha256 verified) and `docker build --check` when a Docker engine is running.
* Commands used by the Docker panel (radide/features/docker_cloud.py): images, containers, logs, start / stop,
  build, run, compose up / down / ps.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

NO_WINDOW = 0x08000000 if os.name == "nt" else 0

HADOLINT_VERSION = "2.12.0"
HADOLINT_ASSET = "hadolint-Windows-x86_64.exe" if os.name == "nt" else "hadolint-Linux-x86_64"
HADOLINT_URL = f"https://github.com/hadolint/hadolint/releases/download/v{HADOLINT_VERSION}/{HADOLINT_ASSET}"

DOCKER_INSTALL_HINT = ("No Docker CLI found. Install Docker Desktop (https://www.docker.com/products/docker-desktop/, "
                       "needs administrator rights) or Podman Desktop (https://podman-desktop.io/), then restart "
                       "RAD IDE. The generators work without Docker; building and running images need it.")


def tools_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "RADIDE" / "tools"


# ====================================================================== process helpers
def run(argv: list[str], cwd=None, timeout: float = 60, env: dict | None = None,
        input_text: str | None = None) -> tuple[int, str, str]:
    """Runs a command and returns (exit code, stdout, stderr). Never raises for a failing command;
    a missing program gives code 127 and a timeout code 124."""
    e = None
    if env:
        e = dict(os.environ)
        e.update(env)
    try:
        p = subprocess.run(argv, cwd=str(cwd) if cwd else None, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, env=e,
                           input=input_text, stdin=None if input_text is not None else subprocess.DEVNULL,
                           creationflags=NO_WINDOW)
        return p.returncode, p.stdout or "", p.stderr or ""
    except FileNotFoundError as ex:
        return 127, "", str(ex)
    except subprocess.TimeoutExpired as ex:
        out = ex.stdout.decode("utf-8", "replace") if isinstance(ex.stdout, bytes) else (ex.stdout or "")
        return 124, out, f"timed out after {timeout:.0f} s"
    except OSError as ex:
        return 126, "", str(ex)


# ====================================================================== CLI detection
@dataclass
class DockerCli:
    name: str                     # "docker" | "podman"
    path: str
    compose: list[str]            # command prefix for compose ([] = none)
    version: str = ""

    def cmd(self, *args: str) -> list[str]:
        return [self.path, *args]

    def compose_cmd(self, *args: str) -> list[str]:
        return [*self.compose, *args] if self.compose else []


_CLI_CACHE: dict[str, DockerCli | None] = {}


def find_cli(refresh: bool = False) -> DockerCli | None:
    """docker first, then podman. Cached; refresh=True detects again."""
    if not refresh and "cli" in _CLI_CACHE:
        return _CLI_CACHE["cli"]
    cli = None
    for name in ("docker", "podman"):
        path = shutil.which(name)
        if not path and os.name == "nt":
            for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),):
                cand = {"docker": Path(base) / "Docker" / "Docker" / "resources" / "bin" / "docker.exe",
                        "podman": Path(base) / "RedHat" / "Podman" / "podman.exe"}[name]
                if cand.is_file():
                    path = str(cand)
        if not path:
            continue
        code, out, _ = run([path, "--version"], timeout=15)
        version = out.strip() if code == 0 else ""
        compose: list[str] = []
        c2, _o, _e = run([path, "compose", "version"], timeout=20)
        if c2 == 0:
            compose = [path, "compose"]
        else:
            alt = shutil.which("docker-compose" if name == "docker" else "podman-compose")
            if alt:
                compose = [alt]
        cli = DockerCli(name, path, compose, version)
        break
    _CLI_CACHE["cli"] = cli
    return cli


def daemon_status(cli: DockerCli | None = None) -> tuple[bool, str]:
    """(True, "Docker 29.x (server 29.x)") when the engine answers, else (False, reason)."""
    cli = cli or find_cli()
    if cli is None:
        return False, DOCKER_INSTALL_HINT
    code, out, err = run(cli.cmd("version", "--format", "{{.Server.Version}}"), timeout=20)
    if code == 0 and out.strip():
        return True, f"{cli.version or cli.name} - engine {out.strip()}"
    msg = (err or out).strip().splitlines()
    hint = ("Start Docker Desktop and wait until it says 'Engine running'." if cli.name == "docker"
            else "Run `podman machine start` in the Terminal.")
    return False, f"The {cli.name} engine is not running. {hint}" + (f"\n({msg[-1]})" if msg else "")


# ====================================================================== stack detection
DESKTOP_LANGS = {"python-tk", "python-qt", "kivy", "pygame", "arcade", "vb-basic", "ring-qt", "ring-game", "flutter",
                 "godot", "csharp", "java", "c", "cpp", "rust", "fortran", "lua", "perl", "dart", "powershell",
                 "html5-game", "expo"}


@dataclass
class Stack:
    kind: str                     # see STACK_LABELS
    port: int = 8000
    details: dict = field(default_factory=dict)
    reason: str = ""              # why it was chosen / why it is skipped

    @property
    def label(self) -> str:
        return STACK_LABELS.get(self.kind, self.kind)

    @property
    def supported(self) -> bool:
        return self.kind in TEMPLATES


STACK_LABELS = {
    "django": "Python - Django", "flask": "Python - Flask", "fastapi": "Python - FastAPI",
    "python-web": "Python web app (WSGI)", "node": "Node.js (Express / any server)", "nextjs": "Next.js",
    "nestjs": "NestJS", "node-static": "Node build -> static site (Vite / React / Vue / Angular)",
    "php": "PHP site (Apache)", "laravel": "PHP - Laravel", "codeigniter": "PHP - CodeIgniter 4",
    "static": "Static HTML / CSS / JS (nginx)", "aspnet": ".NET - ASP.NET Core", "dotnet": ".NET console app",
    "spring-maven": "Java - Spring Boot (Maven)", "spring-gradle": "Java - Spring Boot (Gradle)",
    "rails": "Ruby on Rails", "go": "Go web server", "desktop": "Desktop program (no container)",
    "unknown": "Unknown",
}
DEFAULT_PORTS = {"django": 8000, "flask": 8000, "fastapi": 8000, "python-web": 8000, "node": 3000, "nextjs": 3000,
                 "nestjs": 3000, "node-static": 80, "php": 80, "laravel": 80, "codeigniter": 80, "static": 80,
                 "aspnet": 8080, "dotnet": 0, "spring-maven": 8080, "spring-gradle": 8080, "rails": 3000, "go": 8080}


def _read(p: Path, limit: int = 200_000) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _radproj(folder: Path) -> dict:
    try:
        return json.loads((folder / "project.radproj").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _py_deps(folder: Path) -> str:
    text = ""
    for n in ("requirements.txt", "pyproject.toml", "Pipfile", "setup.py"):
        text += _read(folder / n).lower() + "\n"
    return text


def _find_py_app(folder: Path, marker: str, names=("main.py", "app.py", "wsgi.py", "server.py", "run.py",
                                                    "application.py", "api.py")) -> tuple[str, str]:
    """(module, variable) of the first file creating `marker(`, e.g. ("main", "app") for FastAPI."""
    cands = [folder / n for n in names] + [folder / "app" / n for n in names] + [folder / "src" / n for n in names]
    for p in cands + sorted(folder.glob("*.py"))[:40]:
        text = _read(p)
        m = re.search(r"^(\w+)\s*=\s*" + re.escape(marker) + r"\(", text, re.M)
        if m:
            mod = p.relative_to(folder).with_suffix("").as_posix().replace("/", ".")
            return mod, m.group(1)
        m = re.search(r"^def\s+create_app\s*\(", text, re.M)
        if m and marker == "Flask":
            mod = p.relative_to(folder).with_suffix("").as_posix().replace("/", ".")
            return mod, "create_app()"
    return "", ""


def _package_json(folder: Path) -> dict:
    try:
        return json.loads((folder / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _node_main(folder: Path, pkg: dict) -> str:
    start = str((pkg.get("scripts") or {}).get("start") or "")
    m = re.match(r"node\s+([\w./-]+\.(?:c|m)?js)", start)
    if m:
        return m.group(1)
    if pkg.get("main") and (folder / pkg["main"]).is_file():
        return pkg["main"]
    for n in ("server.js", "app.js", "index.js", "main.js", "src/server.js", "src/index.js", "bin/www"):
        if (folder / n).is_file():
            return n
    return ""


def detect_stack(folder) -> Stack:
    folder = Path(folder)
    proj = _radproj(folder)
    lang = str(proj.get("language") or "")
    web = proj.get("web") if isinstance(proj.get("web"), dict) else {}
    fw = str((web or {}).get("framework") or proj.get("framework") or "").lower()
    # explicit framework written by the framework templates (radide/web_site/frameworks/*)
    explicit = {"django": "django", "flask": "flask", "fastapi": "fastapi", "laravel": "laravel",
                "codeigniter": "codeigniter", "aspnet": "aspnet", "asp.net": "aspnet", "spring": "spring-maven",
                "rails": "rails", "nestjs": "nestjs", "nextjs": "nextjs", "next": "nextjs", "express": "node"}
    if fw in explicit:
        kind = explicit[fw]
        if kind == "spring-maven" and not (folder / "pom.xml").is_file() and \
                ((folder / "build.gradle").is_file() or (folder / "build.gradle.kts").is_file()):
            kind = "spring-gradle"
        return _finish(folder, Stack(kind, reason=f"project.radproj framework = {fw}"))

    pyd = _py_deps(folder)
    if (folder / "manage.py").is_file() and "django" in (_read(folder / "manage.py") + pyd):
        return _finish(folder, Stack("django", reason="manage.py (Django)"))
    if "fastapi" in pyd or _find_py_app(folder, "FastAPI")[0]:
        return _finish(folder, Stack("fastapi", reason="FastAPI in the requirements / code"))
    if "flask" in pyd or _find_py_app(folder, "Flask")[0]:
        return _finish(folder, Stack("flask", reason="Flask in the requirements / code"))

    composer = {}
    try:
        composer = json.loads((folder / "composer.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    req = {**(composer.get("require") or {})}
    if "laravel/framework" in req or (folder / "artisan").is_file():
        return _finish(folder, Stack("laravel", reason="Laravel (artisan / composer.json)"))
    if "codeigniter4/framework" in req or (folder / "spark").is_file():
        return _finish(folder, Stack("codeigniter", reason="CodeIgniter 4 (spark / composer.json)"))

    pkg = _package_json(folder)
    if pkg:
        deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
        if "next" in deps:
            return _finish(folder, Stack("nextjs", reason="next in package.json"))
        if "@nestjs/core" in deps:
            return _finish(folder, Stack("nestjs", reason="@nestjs/core in package.json"))
        server_libs = ("express", "fastify", "koa", "@hapi/hapi", "hono", "restify", "socket.io")
        if any(d in deps for d in server_libs) or _node_main(folder, pkg) or lang == "node-web":
            return _finish(folder, Stack("node", reason="Node.js server (package.json)"))
        if any(d in deps for d in ("vite", "react-scripts", "@angular/core", "@vue/cli-service", "parcel",
                                   "astro", "@sveltejs/kit", "webpack")) and "build" in (pkg.get("scripts") or {}):
            return _finish(folder, Stack("node-static", reason="front-end build (npm run build)"))

    csprojs = sorted(folder.glob("*.csproj")) or sorted(folder.glob("*/*.csproj"))
    if csprojs:
        text = _read(csprojs[0])
        kind = "aspnet" if "Microsoft.NET.Sdk.Web" in text else "dotnet"
        return _finish(folder, Stack(kind, details={"csproj": csprojs[0].relative_to(folder).as_posix()},
                                     reason=f"{csprojs[0].name}"))
    if (folder / "pom.xml").is_file():
        return _finish(folder, Stack("spring-maven", reason="pom.xml"))
    if (folder / "build.gradle").is_file() or (folder / "build.gradle.kts").is_file():
        return _finish(folder, Stack("spring-gradle", reason="build.gradle"))
    if "rails" in _read(folder / "Gemfile").lower():
        return _finish(folder, Stack("rails", reason="rails in the Gemfile"))
    if (folder / "go.mod").is_file():
        return _finish(folder, Stack("go", reason="go.mod"))

    if lang == "php-web" or any(folder.glob("*.php")) or any(folder.glob("public/*.php")):
        return _finish(folder, Stack("php", reason="PHP files" if lang != "php-web" else "PHP Web Site project"))
    if lang == "static-web" or (folder / "index.html").is_file():
        return _finish(folder, Stack("static", reason="index.html"))
    if lang in DESKTOP_LANGS or (proj and proj.get("kind", "app") != "website"):
        return Stack("desktop", 0, reason=f"'{lang or 'desktop'}' projects are desktop programs - a container has "
                                         "no screen for their windows, so no Dockerfile is generated.")
    if any(folder.glob("*.py")) and "tkinter" in "".join(_read(p, 4000) for p in sorted(folder.glob("*.py"))[:10]):
        return Stack("desktop", 0, reason="Tkinter program (desktop) - not containerised.")
    if any(folder.glob("*.py")):
        return _finish(folder, Stack("python-web", reason="Python files (generic WSGI app)"))
    return Stack("unknown", 0, reason="No web framework, server or index.html found.")


def _finish(folder: Path, st: Stack) -> Stack:
    st.port = st.port if st.port and st.port != 8000 else DEFAULT_PORTS.get(st.kind, 8000)
    d = st.details
    if st.kind == "django":
        wsgi = sorted(folder.glob("*/wsgi.py"))
        d["wsgi"] = (wsgi[0].parent.name + ".wsgi:application") if wsgi else "config.wsgi:application"
    elif st.kind in ("flask", "fastapi", "python-web"):
        marker = {"flask": "Flask", "fastapi": "FastAPI", "python-web": "Flask"}[st.kind]
        mod, var = _find_py_app(folder, marker)
        d["module"], d["app"] = mod or ("main" if st.kind == "fastapi" else "app"), var or "app"
    elif st.kind in ("node", "nextjs", "nestjs", "node-static"):
        pkg = _package_json(folder)
        d["main"] = _node_main(folder, pkg)
        d["has_start"] = bool((pkg.get("scripts") or {}).get("start"))
        d["has_build"] = bool((pkg.get("scripts") or {}).get("build"))
        d["lock"] = ("package-lock.json" if (folder / "package-lock.json").is_file() else
                     "yarn.lock" if (folder / "yarn.lock").is_file() else
                     "pnpm-lock.yaml" if (folder / "pnpm-lock.yaml").is_file() else "")
        if st.kind == "node-static":
            deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
            d["out"] = "build" if "react-scripts" in deps else ("dist/browser" if "@angular/core" in deps else "dist")
    elif st.kind in ("php", "laravel", "codeigniter"):
        proj = _radproj(folder)
        root = str(((proj.get("web") or {}) if isinstance(proj.get("web"), dict) else {}).get("root") or ".")
        if st.kind != "php" or (root in (".", "") and (folder / "public" / "index.php").is_file()):
            root = "public"
        d["docroot"] = root.strip("./") or ""
        d["composer"] = (folder / "composer.json").is_file()
        d["pdo_mysql"] = True
    elif st.kind in ("aspnet", "dotnet"):
        cs = folder / d.get("csproj", "")
        text = _read(cs) if cs.is_file() else ""
        m = re.search(r"<TargetFramework>net(\d+\.\d+)</TargetFramework>", text)
        d["dotnet"] = m.group(1) if m else "9.0"
        an = re.search(r"<AssemblyName>([^<]+)</AssemblyName>", text)
        d["assembly"] = an.group(1) if an else (cs.stem if cs.name else "App")
    elif st.kind == "go":
        m = re.search(r"^go\s+(\d+\.\d+)", _read(folder / "go.mod"), re.M)
        d["go"] = m.group(1) if m else "1.23"
    elif st.kind in ("spring-maven", "spring-gradle"):
        text = _read(folder / "pom.xml") + _read(folder / "build.gradle") + _read(folder / "build.gradle.kts")
        m = re.search(r"<java\.version>(\d+)</java\.version>|languageVersion\s*=\s*JavaLanguageVersion\.of\((\d+)\)"
                      r"|sourceCompatibility\s*=\s*['\"]?(?:JavaVersion\.VERSION_)?(\d+)", text)
        d["java"] = next((g for g in (m.groups() if m else ()) if g), "21")
        d["wrapper"] = (folder / ("mvnw" if st.kind == "spring-maven" else "gradlew")).is_file()
    elif st.kind == "rails":
        m = re.search(r"ruby\s+['\"](\d+\.\d+)", _read(folder / "Gemfile"))
        d["ruby"] = m.group(1) if m else "3.3"
    return st


# ====================================================================== generators
@dataclass
class DockerOptions:
    port: int = 0                     # 0 = default of the stack
    database: str = "none"            # none | postgres | mysql | mariadb | redis | mongo
    python: str = "3.12"
    node: str = "22"
    php: str = "8.3"
    compose: bool = True
    devcontainer: bool = True
    watch: bool = True                # compose "develop: watch" (docker compose watch) for live sync
    base_image: str = ""              # override the runtime FROM image (advanced / tests)
    service: str = "web"


def _py_requirements(folder: Path, kind: str) -> tuple[bool, str]:
    """(has requirements.txt, extra pip packages needed by the server command)."""
    has = (folder / "requirements.txt").is_file()
    deps = _py_deps(folder)
    extra = []
    if kind in ("django", "flask", "python-web") and "gunicorn" not in deps:
        extra.append("gunicorn==23.0.0")
    if kind == "fastapi" and "uvicorn" not in deps:
        extra.append("uvicorn==0.32.1")
    return has, " ".join(extra)


def _t_python(folder: Path, st: Stack, o: DockerOptions) -> str:
    has_req, extra = _py_requirements(folder, st.kind)
    port = o.port or st.port
    d = st.details
    if st.kind == "django":
        cmd = f'["gunicorn", "--bind", "0.0.0.0:{port}", "--workers", "3", "{d.get("wsgi")}"]'
    elif st.kind == "fastapi":
        cmd = f'["uvicorn", "{d.get("module")}:{d.get("app")}", "--host", "0.0.0.0", "--port", "{port}"]'
    else:
        target = f'{d.get("module")}:{d.get("app")}'
        cmd = f'["gunicorn", "--bind", "0.0.0.0:{port}", "--workers", "3", "{target}"]'
    lines = ["# syntax=docker/dockerfile:1",
             f"# {st.label} - generated by RAD IDE (Docker > Generate Dockerfile). Edit freely.",
             f"FROM {o.base_image or f'python:{o.python}-slim'}",
             "",
             "ENV PYTHONDONTWRITEBYTECODE=1 \\",
             "    PYTHONUNBUFFERED=1 \\",
             "    PIP_DISABLE_PIP_VERSION_CHECK=1",
             "WORKDIR /app", ""]
    if has_req:
        lines += ["COPY requirements.txt ./",
                  "RUN pip install --no-cache-dir -r requirements.txt" + (f" \\\n    && pip install --no-cache-dir {extra}"
                                                                        if extra else "")]
    else:
        base_pkg = {"django": "django==5.1.4", "flask": "flask==3.1.0", "fastapi": "fastapi==0.115.6",
                    "python-web": "flask==3.1.0"}[st.kind]
        lines += [f"RUN pip install --no-cache-dir {base_pkg} {extra}".rstrip()]
    lines += ["", "COPY . .", ""]
    if st.kind == "django":
        lines += ["# static files for production (needs STATIC_ROOT in settings.py)",
                  "RUN python manage.py collectstatic --noinput || echo \"collectstatic skipped\"", ""]
    lines += ["RUN useradd --create-home --uid 10001 app && chown -R app /app",
              "USER app", "", f"EXPOSE {port}", f"CMD {cmd}", ""]
    return "\n".join(lines)


def _npm_install(d: dict, dev: bool) -> str:
    lock = d.get("lock")
    if lock == "yarn.lock":
        return "corepack enable && yarn install --frozen-lockfile" + ("" if dev else " --production")
    if lock == "pnpm-lock.yaml":
        return "corepack enable && pnpm install --frozen-lockfile" + ("" if dev else " --prod")
    if lock:
        return "npm ci" + ("" if dev else " --omit=dev")
    return "npm install" + ("" if dev else " --omit=dev")


def _t_node(folder: Path, st: Stack, o: DockerOptions) -> str:
    d, port = st.details, o.port or st.port
    node_img = f"node:{o.node}-alpine"
    head = ["# syntax=docker/dockerfile:1", f"# {st.label} - generated by RAD IDE (Docker > Generate Dockerfile)."]
    copy_pkg = "COPY package*.json " + ("yarn.lock " if d.get("lock") == "yarn.lock" else "") + \
               ("pnpm-lock.yaml " if d.get("lock") == "pnpm-lock.yaml" else "") + "./"
    if st.kind == "node":
        cmd = '["npm", "start"]' if d.get("has_start") else f'["node", "{d.get("main") or "server.js"}"]'
        return "\n".join(head + [
            f"FROM {o.base_image or node_img}", "ENV NODE_ENV=production", "WORKDIR /app", "",
            copy_pkg, f"RUN {_npm_install(d, dev=False)}", "", "COPY --chown=node:node . .", "",
            "USER node", f"ENV PORT={port}", f"EXPOSE {port}", f"CMD {cmd}", ""])
    if st.kind == "nextjs":
        return "\n".join(head + [
            f"FROM {node_img} AS build", "WORKDIR /app", copy_pkg, f"RUN {_npm_install(d, dev=True)}",
            "COPY . .", "RUN npm run build", "",
            f"FROM {o.base_image or node_img}", "ENV NODE_ENV=production", "WORKDIR /app",
            "COPY --from=build --chown=node:node /app ./", "USER node", f"ENV PORT={port}", f"EXPOSE {port}",
            'CMD ["npm", "start"]', ""])
    if st.kind == "nestjs":
        return "\n".join(head + [
            f"FROM {node_img} AS build", "WORKDIR /app", copy_pkg, f"RUN {_npm_install(d, dev=True)}",
            "COPY . .", "RUN npm run build", "",
            f"FROM {o.base_image or node_img}", "ENV NODE_ENV=production", "WORKDIR /app",
            copy_pkg, f"RUN {_npm_install(d, dev=False)}",
            "COPY --from=build --chown=node:node /app/dist ./dist", "USER node", f"ENV PORT={port}",
            f"EXPOSE {port}", 'CMD ["node", "dist/main.js"]', ""])
    # node-static: build with Node, serve with nginx
    return "\n".join(head + [
        f"FROM {node_img} AS build", "WORKDIR /app", copy_pkg, f"RUN {_npm_install(d, dev=True)}",
        "COPY . .", "RUN npm run build", "",
        f"FROM {o.base_image or 'nginx:1.27-alpine'}",
        f"COPY --from=build /app/{d.get('out', 'dist')} /usr/share/nginx/html", "EXPOSE 80",
        'CMD ["nginx", "-g", "daemon off;"]', ""])


def _t_php(folder: Path, st: Stack, o: DockerOptions) -> str:
    d = st.details
    docroot = d.get("docroot") or ""
    lines = ["# syntax=docker/dockerfile:1", f"# {st.label} - generated by RAD IDE (Docker > Generate Dockerfile)."]
    framework = st.kind in ("laravel", "codeigniter")
    if d.get("composer"):
        lines += ["FROM composer:2 AS vendor", "WORKDIR /app", "COPY composer.json composer.lock* ./",
                  "RUN composer install --no-dev --no-interaction --no-scripts --prefer-dist --optimize-autoloader "
                  "--ignore-platform-reqs", ""]
    lines += [f"FROM {o.base_image or f'php:{o.php}-apache'}", ""]
    exts = ["pdo_mysql"] + (["bcmath"] if st.kind == "laravel" else [])
    lines += [f"RUN docker-php-ext-install {' '.join(exts)} && a2enmod rewrite", ""]
    if docroot:
        lines += [f"ENV APACHE_DOCUMENT_ROOT=/var/www/html/{docroot}",
                  "RUN sed -ri -e 's!/var/www/html!${APACHE_DOCUMENT_ROOT}!g' /etc/apache2/sites-available/*.conf \\",
                  "    && sed -ri -e 's!/var/www/!${APACHE_DOCUMENT_ROOT}!g' /etc/apache2/apache2.conf "
                  "/etc/apache2/conf-available/*.conf", ""]
    lines += ["# allow .htaccess (pretty URLs)",
              "RUN sed -ri -e 's!AllowOverride None!AllowOverride All!g' /etc/apache2/apache2.conf", "",
              "WORKDIR /var/www/html", "COPY . ."]
    if d.get("composer"):
        lines += ["COPY --from=vendor /app/vendor ./vendor"]
    writable = {"laravel": "storage bootstrap/cache", "codeigniter": "writable"}.get(st.kind, "")
    if not framework and (folder / "data").is_dir():
        writable = "data"
    if writable:
        lines += [f"RUN chown -R www-data:www-data {writable}"]
    lines += ["", "EXPOSE 80", ""]
    return "\n".join(lines)


def _t_static(folder: Path, st: Stack, o: DockerOptions) -> str:
    return "\n".join(["# syntax=docker/dockerfile:1",
                      f"# {st.label} - generated by RAD IDE (Docker > Generate Dockerfile).",
                      f"FROM {o.base_image or 'nginx:1.27-alpine'}",
                      "COPY . /usr/share/nginx/html", "EXPOSE 80", 'CMD ["nginx", "-g", "daemon off;"]', ""])


def _t_dotnet(folder: Path, st: Stack, o: DockerOptions) -> str:
    d, port = st.details, o.port or st.port
    ver, asm, csproj = d.get("dotnet", "9.0"), d.get("assembly", "App"), d.get("csproj", "App.csproj")
    runtime = "aspnet" if st.kind == "aspnet" else "runtime"
    lines = ["# syntax=docker/dockerfile:1", f"# {st.label} - generated by RAD IDE (Docker > Generate Dockerfile).",
             f"FROM mcr.microsoft.com/dotnet/sdk:{ver} AS build", "WORKDIR /src",
             f"COPY {csproj} ./{(Path(csproj).parent.as_posix() + '/') if '/' in csproj else ''}",
             f"RUN dotnet restore \"{csproj}\"", "COPY . .",
             f"RUN dotnet publish \"{csproj}\" -c Release -o /app/publish /p:UseAppHost=false", "",
             f"FROM {o.base_image or f'mcr.microsoft.com/dotnet/{runtime}:{ver}'}", "WORKDIR /app",
             "COPY --from=build /app/publish ."]
    if st.kind == "aspnet":
        lines += [f"ENV ASPNETCORE_HTTP_PORTS={port}", f"EXPOSE {port}"]
    lines += ["USER $APP_UID", f'ENTRYPOINT ["dotnet", "{asm}.dll"]', ""]
    return "\n".join(lines)


def _t_java(folder: Path, st: Stack, o: DockerOptions) -> str:
    d, port = st.details, o.port or st.port
    jv = d.get("java", "21")
    if st.kind == "spring-maven":
        build = [f"FROM maven:3.9-eclipse-temurin-{jv} AS build", "WORKDIR /src", "COPY pom.xml ./",
                 "RUN mvn -q -B dependency:go-offline", "COPY src ./src", "RUN mvn -q -B -DskipTests package",
                 ""]
        jar = "/src/target/*.jar"
    else:
        build = [f"FROM gradle:8-jdk{jv} AS build", "WORKDIR /src", "COPY . .",
                 "RUN gradle --no-daemon -q bootJar -x test", ""]
        jar = "/src/build/libs/*.jar"
    return "\n".join(["# syntax=docker/dockerfile:1",
                      f"# {st.label} - generated by RAD IDE (Docker > Generate Dockerfile)."] + build + [
        f"FROM {o.base_image or f'eclipse-temurin:{jv}-jre'}", "WORKDIR /app", f"COPY --from=build {jar} app.jar",
        "RUN useradd --uid 10001 app", "USER app", f"EXPOSE {port}", f'ENV SERVER_PORT={port}',
        'ENTRYPOINT ["java", "-jar", "/app/app.jar"]', ""])


def _t_rails(folder: Path, st: Stack, o: DockerOptions) -> str:
    rv, port = st.details.get("ruby", "3.3"), o.port or st.port
    return "\n".join([
        "# syntax=docker/dockerfile:1", f"# {st.label} - generated by RAD IDE (Docker > Generate Dockerfile).",
        f"FROM {o.base_image or f'ruby:{rv}-slim'}",
        "# distribution packages follow the base image's security updates (not pinned on purpose)",
        "# hadolint ignore=DL3008",
        "RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev libyaml-dev "
        "git && rm -rf /var/lib/apt/lists/*",
        "ENV RAILS_ENV=production BUNDLE_WITHOUT=development:test", "WORKDIR /rails",
        "COPY Gemfile Gemfile.lock* ./", "RUN bundle install", "COPY . .",
        "RUN SECRET_KEY_BASE_DUMMY=1 bundle exec rails assets:precompile || echo \"no assets\"",
        "RUN useradd --create-home --uid 10001 rails && chown -R rails /rails", "USER rails",
        f"EXPOSE {port}", f'CMD ["bundle", "exec", "rails", "server", "-b", "0.0.0.0", "-p", "{port}"]', ""])


def _t_go(folder: Path, st: Stack, o: DockerOptions) -> str:
    gv, port = st.details.get("go", "1.23"), o.port or st.port
    return "\n".join([
        "# syntax=docker/dockerfile:1", f"# {st.label} - generated by RAD IDE (Docker > Generate Dockerfile).",
        f"FROM golang:{gv}-alpine AS build", "WORKDIR /src", "COPY go.* ./", "RUN go mod download", "COPY . .",
        "RUN CGO_ENABLED=0 go build -o /out/app .", "",
        f"FROM {o.base_image or 'gcr.io/distroless/static-debian12:nonroot'}", "COPY --from=build /out/app /app",
        f"ENV PORT={port}", f"EXPOSE {port}", "USER nonroot:nonroot", 'ENTRYPOINT ["/app"]', ""])


TEMPLATES = {"django": _t_python, "flask": _t_python, "fastapi": _t_python, "python-web": _t_python,
             "node": _t_node, "nextjs": _t_node, "nestjs": _t_node, "node-static": _t_node,
             "php": _t_php, "laravel": _t_php, "codeigniter": _t_php, "static": _t_static,
             "aspnet": _t_dotnet, "dotnet": _t_dotnet, "spring-maven": _t_java, "spring-gradle": _t_java,
             "rails": _t_rails, "go": _t_go}

IGNORE_COMMON = [".git", ".gitignore", ".radide", ".radide_backup*", ".vscode", ".idea", "*.log", "Dockerfile*",
                 ".dockerignore", "compose*.yaml", "docker-compose*.yml", ".devcontainer", ".env", ".env.*",
                 "Thumbs.db", ".DS_Store"]
IGNORE_BY_KIND = {
    "python": ["__pycache__", "*.pyc", ".venv", "venv", "env", ".pytest_cache", ".mypy_cache", "db.sqlite3",
               "staticfiles"],
    "node": ["node_modules", "npm-debug.log", ".next", "dist", "build", "coverage"],
    "php": ["vendor", "node_modules", "storage/logs/*", "writable/logs/*", "data/*.sqlite"],
    "static": ["node_modules"],
    "dotnet": ["bin", "obj", "*.user"],
    "java": ["target", "build", ".gradle"],
    "rails": ["log/*", "tmp/*", "node_modules", "storage/*"],
    "go": ["bin"],
}
FAMILY = {"django": "python", "flask": "python", "fastapi": "python", "python-web": "python", "node": "node",
          "nextjs": "node", "nestjs": "node", "node-static": "node", "php": "php", "laravel": "php",
          "codeigniter": "php", "static": "static", "aspnet": "dotnet", "dotnet": "dotnet", "spring-maven": "java",
          "spring-gradle": "java", "rails": "rails", "go": "go"}


def dockerfile(folder, stack: Stack | None = None, options: DockerOptions | None = None) -> str:
    folder = Path(folder)
    st = stack or detect_stack(folder)
    if not st.supported:
        raise ValueError(st.reason or f"No Dockerfile template for '{st.kind}'.")
    return TEMPLATES[st.kind](folder, st, options or DockerOptions())


def dockerignore(stack: Stack) -> str:
    fam = FAMILY.get(stack.kind, "")
    lines = ["# generated by RAD IDE - files that are not sent to `docker build`"] + IGNORE_COMMON + \
        IGNORE_BY_KIND.get(fam, [])
    return "\n".join(lines) + "\n"


DB_SERVICES = {
    "postgres": ("postgres:16-alpine", {"POSTGRES_USER": "app", "POSTGRES_PASSWORD": "change-me",
                                        "POSTGRES_DB": "app"}, "/var/lib/postgresql/data", 5432,
                 "postgresql://app:change-me@db:5432/app"),
    "mysql": ("mysql:8.4", {"MYSQL_DATABASE": "app", "MYSQL_USER": "app", "MYSQL_PASSWORD": "change-me",
                            "MYSQL_ROOT_PASSWORD": "change-me-root"}, "/var/lib/mysql", 3306,
              "mysql://app:change-me@db:3306/app"),
    "mariadb": ("mariadb:11", {"MARIADB_DATABASE": "app", "MARIADB_USER": "app", "MARIADB_PASSWORD": "change-me",
                               "MARIADB_ROOT_PASSWORD": "change-me-root"}, "/var/lib/mysql", 3306,
                "mysql://app:change-me@db:3306/app"),
    "redis": ("redis:7-alpine", {}, "/data", 6379, "redis://db:6379/0"),
    "mongo": ("mongo:8", {}, "/data/db", 27017, "mongodb://db:27017/app"),
}
_WORKDIR = {"python": "/app", "node": "/app", "php": "/var/www/html", "static": "/usr/share/nginx/html",
            "rails": "/rails"}


def _yq(v) -> str:
    """A YAML scalar, always double-quoted (safe for any text)."""
    return json.dumps(str(v), ensure_ascii=False)


def compose_yaml(folder, stack: Stack, options: DockerOptions | None = None) -> str:
    o = options or DockerOptions()
    port = o.port or stack.port or 8080
    cport = port
    if stack.kind in ("php", "laravel", "codeigniter", "static", "node-static"):
        cport = 80
    host_port = port if port != 80 else 8080
    name = re.sub(r"[^a-z0-9_-]", "", Path(folder).name.lower()) or "app"
    svc = o.service or "web"
    lines = ["# generated by RAD IDE (Docker > Generate Dockerfile). `docker compose up --build` runs the app.",
             f"name: {_yq(name)}", "services:", f"  {svc}:", "    build: .",
             "    ports:", f"      - {_yq(f'{host_port}:{cport}')}"]
    env: dict[str, str] = {}
    db = DB_SERVICES.get(o.database)
    if db:
        env["DATABASE_URL"] = db[4]
        if stack.kind == "laravel" and o.database in ("mysql", "mariadb", "postgres"):
            env.update({"DB_CONNECTION": "pgsql" if o.database == "postgres" else "mysql", "DB_HOST": "db",
                        "DB_DATABASE": "app", "DB_USERNAME": "app", "DB_PASSWORD": "change-me"})
    if stack.kind == "django":
        env.setdefault("DJANGO_DEBUG", "0")
    if env:
        lines.append("    environment:")
        lines += [f"      {k}: {_yq(v)}" for k, v in env.items()]
    if db:
        lines += ["    depends_on:", "      - db"]
    fam = FAMILY.get(stack.kind, "")
    if o.watch and fam in _WORKDIR and stack.kind not in ("node-static", "nextjs", "nestjs"):
        ign = {"python": ["__pycache__/", ".venv/"], "node": ["node_modules/"], "php": ["vendor/"],
               "static": [], "rails": ["tmp/", "log/"]}[fam]
        lines += ["    develop:", "      watch:", "        - action: sync", "          path: .",
                  f"          target: {_WORKDIR[fam]}"]
        if ign:
            lines.append("          ignore:")
            lines += [f"            - {_yq(i)}" for i in ign]
        rebuild = {"python": "requirements.txt", "node": "package.json", "php": "composer.json",
                   "rails": "Gemfile"}.get(fam)
        if rebuild and (Path(folder) / rebuild).is_file():
            lines += ["        - action: rebuild", f"          path: {rebuild}"]
    lines.append("    restart: unless-stopped")
    if db:
        image, denv, vol, _p, _u = db
        lines += ["  db:", f"    image: {image}"]
        if denv:
            lines.append("    environment:")
            lines += [f"      {k}: {_yq(v)}" for k, v in denv.items()]
        lines += ["    volumes:", f"      - db-data:{vol}", "    restart: unless-stopped", "volumes:", "  db-data: {}"]
    return "\n".join(lines) + "\n"


DEVCONTAINER_IMAGES = {
    "python": "mcr.microsoft.com/devcontainers/python:1-{python}-bookworm",
    "node": "mcr.microsoft.com/devcontainers/javascript-node:1-{node}-bookworm",
    "php": "mcr.microsoft.com/devcontainers/php:1-{php}-bookworm",
    "static": "mcr.microsoft.com/devcontainers/javascript-node:1-{node}-bookworm",
    "dotnet": "mcr.microsoft.com/devcontainers/dotnet:1-{dotnet}-bookworm",
    "java": "mcr.microsoft.com/devcontainers/java:1-{java}-bookworm",
    "rails": "mcr.microsoft.com/devcontainers/ruby:1-{ruby}-bookworm",
    "go": "mcr.microsoft.com/devcontainers/go:1-{go}-bookworm",
}
DEVCONTAINER_SETUP = {
    "python": "pip install --user -r requirements.txt", "node": "npm install", "php": "composer install",
    "static": "", "dotnet": "dotnet restore", "java": "", "rails": "bundle install", "go": "go mod download",
}
DEVCONTAINER_EXT = {
    "python": ["ms-python.python", "ms-python.debugpy"], "node": ["dbaeumer.vscode-eslint"],
    "php": ["bmewburn.vscode-intelephense-client", "xdebug.php-debug"], "static": ["ritwickdey.LiveServer"],
    "dotnet": ["ms-dotnettools.csharp"], "java": ["vscjava.vscode-java-pack"], "rails": ["Shopify.ruby-lsp"],
    "go": ["golang.go"],
}


def devcontainer_json(folder, stack: Stack, options: DockerOptions | None = None, use_compose: bool = False) -> str:
    o = options or DockerOptions()
    fam = FAMILY.get(stack.kind, "static")
    d = stack.details
    vers = {"python": o.python, "node": o.node, "php": o.php, "dotnet": d.get("dotnet", "9.0"),
            "java": d.get("java", "21"), "ruby": d.get("ruby", "3.3"), "go": d.get("go", "1.23")}
    port = o.port or stack.port or 8000
    cfg: dict = {"name": f"{Path(folder).name} ({stack.label})"}
    if use_compose:
        cfg.update({"dockerComposeFile": ["../compose.yaml"], "service": o.service or "web",
                    "workspaceFolder": _WORKDIR.get(fam, "/workspace")})
    else:
        cfg["image"] = DEVCONTAINER_IMAGES.get(fam, DEVCONTAINER_IMAGES["static"]).format(**vers)
    cfg["forwardPorts"] = [port if stack.kind not in ("php", "laravel", "codeigniter", "static") else 8080]
    setup = DEVCONTAINER_SETUP.get(fam, "")
    if fam == "php" and not d.get("composer"):
        setup = ""
    if setup and not (fam == "python" and not (Path(folder) / "requirements.txt").is_file()):
        cfg["postCreateCommand"] = setup
    if fam == "php" and not use_compose:
        root = d.get("docroot") or "."
        cfg["postAttachCommand"] = f"php -S 0.0.0.0:8080 -t {root}"
    cfg["customizations"] = {"vscode": {"extensions": DEVCONTAINER_EXT.get(fam, [])}}
    return json.dumps(cfg, indent=2) + "\n"


def generate(folder, stack: Stack | None = None, options: DockerOptions | None = None) -> dict[str, str]:
    """All files for the project: {relative path: content}. Raises ValueError for desktop / unknown projects."""
    folder = Path(folder)
    o = options or DockerOptions()
    st = stack or detect_stack(folder)
    files = {"Dockerfile": dockerfile(folder, st, o), ".dockerignore": dockerignore(st)}
    if o.compose:
        files["compose.yaml"] = compose_yaml(folder, st, o)
    if o.devcontainer:
        files[".devcontainer/devcontainer.json"] = devcontainer_json(folder, st, o)
    return files


def write_files(folder, files: dict[str, str], overwrite: bool = False) -> tuple[list[str], list[str]]:
    """Writes the files. Existing files are kept unless overwrite=True (a .bak copy is made then)."""
    folder = Path(folder)
    written, skipped = [], []
    for rel, text in files.items():
        p = folder / rel
        if p.exists() and not overwrite:
            skipped.append(rel)
            continue
        if p.exists():
            shutil.copy2(p, p.with_name(p.name + ".bak"))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
        written.append(rel)
    return written, skipped


# ====================================================================== lint
@dataclass
class Issue:
    line: int
    level: str        # error | warning | info
    code: str
    message: str
    source: str = "radide"

    def __str__(self) -> str:
        return f"line {self.line}: {self.level} {self.code}: {self.message} [{self.source}]"


INSTRUCTIONS = {"FROM", "RUN", "CMD", "LABEL", "MAINTAINER", "EXPOSE", "ENV", "ADD", "COPY", "ENTRYPOINT", "VOLUME",
                "USER", "WORKDIR", "ARG", "ONBUILD", "STOPSIGNAL", "HEALTHCHECK", "SHELL"}


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """Dockerfile logical lines (continuations joined, comments dropped) with their first line number."""
    out, buf, start = [], "", 0
    escape = "\\"
    m = re.match(r"\s*#\s*escape\s*=\s*(\S)", text)
    if m:
        escape = m.group(1)
    for i, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if not buf and (not s or s.startswith("#")):
            continue
        if buf and s.startswith("#"):
            continue
        if not buf:
            start = i
        if s.endswith(escape):
            buf += s[:-1] + " "
            continue
        buf += s
        out.append((start, buf))
        buf = ""
    if buf:
        out.append((start, buf))
    return out


def lint_builtin(text: str) -> list[Issue]:
    issues: list[Issue] = []
    lines = _logical_lines(text)
    if not lines:
        return [Issue(1, "error", "RD001", "The Dockerfile is empty.")]
    stages: set[str] = set()
    seen_from = False
    cmds = 0
    for n, line in lines:
        parts = line.split(None, 1)
        instr = parts[0].upper()
        args = parts[1] if len(parts) > 1 else ""
        if instr not in INSTRUCTIONS:
            issues.append(Issue(n, "error", "RD002", f"Unknown instruction '{parts[0]}'."))
            continue
        if parts[0] != instr:
            issues.append(Issue(n, "info", "RD003", f"Instructions are usually upper case ({instr})."))
        if not seen_from and instr not in ("FROM", "ARG"):
            issues.append(Issue(n, "error", "RD004", f"{instr} before the first FROM."))
        if instr == "FROM":
            seen_from = True
            cmds = 0
            m = re.match(r"(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?\s*$", args, re.I)
            if not m:
                issues.append(Issue(n, "error", "RD005", "FROM needs an image: FROM <image>[:tag] [AS name]."))
                continue
            image = m.group(1)
            if m.group(2):
                stages.add(m.group(2).lower())
            if image.lower() in stages or "$" in image or image == "scratch":
                pass
            elif ":" not in image.split("/")[-1] and "@" not in image:
                issues.append(Issue(n, "warning", "RD006", f"Pin a version: '{image}' means '{image}:latest'."))
            elif image.endswith(":latest"):
                issues.append(Issue(n, "warning", "RD006", "Pin a version instead of ':latest'."))
        elif instr in ("CMD", "ENTRYPOINT", "RUN", "SHELL") and args.lstrip().startswith("["):
            try:
                v = json.loads(args)
                if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                    raise ValueError
            except ValueError:
                issues.append(Issue(n, "error", "RD007", f"{instr} JSON form is not a valid JSON string array."))
        if instr in ("CMD", "ENTRYPOINT"):
            if instr == "CMD":
                cmds += 1
                if cmds > 1:
                    issues.append(Issue(n, "warning", "RD008", "Several CMD in one stage: only the last one counts."))
            if not args.strip():
                issues.append(Issue(n, "error", "RD009", f"{instr} without a command."))
        elif instr == "EXPOSE":
            for p in args.split():
                if not re.fullmatch(r"(\d+(-\d+)?|\$\{?\w+\}?)(/(tcp|udp))?", p):
                    issues.append(Issue(n, "error", "RD010", f"EXPOSE: '{p}' is not a port number."))
        elif instr in ("COPY", "ADD"):
            m = re.search(r"--from=(\S+)", args)
            if m:
                src = m.group(1).lower()
                if not src.isdigit() and src not in stages and "/" not in src and ":" not in src:
                    issues.append(Issue(n, "error", "RD011", f"COPY --from={m.group(1)}: no stage with that name."))
            plain = [a for a in args.split() if not a.startswith("--")]
            if not args.lstrip().startswith("[") and len(plain) < 2:
                issues.append(Issue(n, "error", "RD012", f"{instr} needs a source and a destination."))
        elif instr == "WORKDIR" and not args.strip():
            issues.append(Issue(n, "error", "RD013", "WORKDIR without a path."))
        elif instr == "RUN":
            if re.search(r"\bapt-get\s+install\b", args) and not re.search(r"\s-y\b|--yes|--assume-yes", args):
                issues.append(Issue(n, "error", "RD014", "apt-get install needs -y (builds cannot answer prompts)."))
            if re.search(r"(^|&&|;)\s*cd\s", args):
                issues.append(Issue(n, "info", "RD015", "Prefer WORKDIR over 'cd' in RUN."))
        elif instr == "MAINTAINER":
            issues.append(Issue(n, "info", "RD016", "MAINTAINER is deprecated: use LABEL maintainer=..."))
    if not seen_from:
        issues.append(Issue(1, "error", "RD004", "No FROM instruction."))
    return issues


def hadolint_path() -> str:
    exe = tools_root() / "hadolint" / ("hadolint.exe" if os.name == "nt" else "hadolint")
    if exe.is_file():
        return str(exe)
    return shutil.which("hadolint") or ""


def install_hadolint(log=print) -> str:
    """Downloads the official hadolint release binary (GitHub hadolint/hadolint) and verifies its published
    sha256. Returns the path or ""."""
    found = hadolint_path()
    if found:
        return found
    dest_dir = tools_root() / "hadolint"
    dest_dir.mkdir(parents=True, exist_ok=True)
    exe = dest_dir / ("hadolint.exe" if os.name == "nt" else "hadolint")
    try:
        log(f"Downloading hadolint {HADOLINT_VERSION} from {HADOLINT_URL} ...")
        req = urllib.request.Request(HADOLINT_URL + ".sha256", headers={"User-Agent": "RAD-IDE"})
        with urllib.request.urlopen(req, timeout=60) as r:
            expected = r.read().decode("ascii", "replace").split()[0].lower()
        tmp = exe.with_suffix(".part")
        req = urllib.request.Request(HADOLINT_URL, headers={"User-Agent": "RAD-IDE"})
        h = hashlib.sha256()
        with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                h.update(chunk)
                f.write(chunk)
        if h.hexdigest().lower() != expected:
            tmp.unlink(missing_ok=True)
            log(f"hadolint checksum mismatch (expected {expected}, got {h.hexdigest()}) - not installed.")
            return ""
        tmp.replace(exe)
        if os.name != "nt":
            exe.chmod(0o755)
        (dest_dir / "SOURCE.txt").write_text(f"{HADOLINT_URL}\nversion {HADOLINT_VERSION}\nsha256 {expected}\n",
                                            encoding="utf-8")
        log(f"hadolint installed: {exe} (sha256 verified)")
        return str(exe)
    except OSError as ex:
        log(f"hadolint download failed: {ex}")
        return ""


def lint_hadolint(path, exe: str = "") -> list[Issue] | None:
    """None when hadolint is not available."""
    exe = exe or hadolint_path()
    if not exe:
        return None
    code, out, err = run([exe, "--no-fail", "--format", "json", str(path)], timeout=60)
    try:
        data = json.loads(out or "[]")
    except ValueError:
        return [Issue(1, "error", "hadolint", (err or out).strip()[:300] or f"hadolint exit {code}", "hadolint")]
    lv = {"error": "error", "warning": "warning", "info": "info", "style": "info"}
    return [Issue(int(d.get("line") or 1), lv.get(d.get("level"), "warning"), d.get("code", ""),
                  d.get("message", ""), "hadolint") for d in data]


def lint_docker_check(folder, dockerfile_name: str = "Dockerfile", cli: DockerCli | None = None,
                      timeout: float = 180) -> list[Issue] | None:
    """`docker build --check` (BuildKit checks, no image is built). None when docker / the engine is missing."""
    cli = cli or find_cli()
    if cli is None or cli.name != "docker" or not daemon_status(cli)[0]:
        return None
    code, out, err = run(cli.cmd("build", "--check", "-f", dockerfile_name, "."), cwd=folder, timeout=timeout)
    text = (out + "\n" + err)
    issues = []
    for m in re.finditer(r"WARNING: (\w+) - (\S+)\n(.*?)(?:\n\n|\Z)", text, re.S):
        detail = " ".join(m.group(3).split())[:300]
        ln = re.search(r":(\d+)\n", text[m.end():m.end() + 300])
        issues.append(Issue(int(ln.group(1)) if ln else 1, "warning", m.group(1), detail or m.group(1), "docker"))
    if code != 0 and not issues:
        msg = [s for s in text.splitlines() if "ERROR" in s or "error" in s.lower()]
        issues.append(Issue(1, "error", "build-check", (msg[-1] if msg else text.strip()[-300:]) or f"exit {code}",
                            "docker"))
    return issues


def lint(folder, dockerfile_name: str = "Dockerfile", use_hadolint: bool = True, use_docker: bool = False
         ) -> tuple[list[Issue], list[str]]:
    """All available linters. Returns (issues, notes about which linters ran)."""
    path = Path(folder) / dockerfile_name
    text = _read(path)
    issues = lint_builtin(text)
    notes = ["built-in checker"]
    if use_hadolint:
        h = lint_hadolint(path)
        if h is None:
            notes.append("hadolint not installed (Docker panel > Lint > Get hadolint)")
        else:
            issues += h
            notes.append("hadolint")
    if use_docker:
        d = lint_docker_check(folder, dockerfile_name)
        if d is None:
            notes.append("docker build --check skipped (no running engine)")
        else:
            issues += d
            notes.append("docker build --check")
    return issues, notes


def validate_compose(folder, file: str = "compose.yaml", cli: DockerCli | None = None) -> tuple[bool, str]:
    cli = cli or find_cli()
    if cli is None or not cli.compose:
        return False, "no docker compose"
    code, out, err = run(cli.compose_cmd("-f", file, "config", "--quiet"), cwd=folder, timeout=60)
    return code == 0, (err or out).strip() or "compose file is valid"


# ====================================================================== panel commands
def list_containers(cli: DockerCli | None = None, all_: bool = True) -> list[dict]:
    cli = cli or find_cli()
    if cli is None:
        return []
    args = ["ps", "--format", "{{json .}}", "--no-trunc"] + (["-a"] if all_ else [])
    code, out, _ = run(cli.cmd(*args), timeout=30)
    return _json_lines(out) if code == 0 else []


def list_images(cli: DockerCli | None = None) -> list[dict]:
    cli = cli or find_cli()
    if cli is None:
        return []
    code, out, _ = run(cli.cmd("images", "--format", "{{json .}}"), timeout=30)
    return _json_lines(out) if code == 0 else []


def compose_ps(folder, file: str = "compose.yaml", cli: DockerCli | None = None) -> list[dict]:
    cli = cli or find_cli()
    if cli is None or not cli.compose:
        return []
    code, out, _ = run(cli.compose_cmd("-f", file, "ps", "-a", "--format", "json"), cwd=folder, timeout=30)
    if code != 0:
        return []
    out = out.strip()
    if out.startswith("["):
        try:
            return json.loads(out)
        except ValueError:
            return []
    return _json_lines(out)


def _json_lines(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def image_tag_for(folder) -> str:
    name = re.sub(r"[^a-z0-9_.-]", "-", Path(folder).name.lower()).strip("-.") or "app"
    return f"{name}:dev"


def build_cmd(cli: DockerCli, folder, tag: str = "", dockerfile_name: str = "Dockerfile") -> list[str]:
    return cli.cmd("build", "-t", tag or image_tag_for(folder), "-f", dockerfile_name, str(folder))


def run_cmd(cli: DockerCli, image: str, host_port: int = 0, container_port: int = 0, name: str = "",
            detach: bool = True) -> list[str]:
    args = ["run", "--rm"] + (["-d"] if detach else []) + (["--name", name] if name else [])
    if container_port:
        args += ["-p", f"127.0.0.1:{host_port or container_port}:{container_port}"]
    return cli.cmd(*args, image)


def container_action_cmd(cli: DockerCli, action: str, container: str) -> list[str]:
    if action not in ("start", "stop", "restart", "rm", "pause", "unpause", "kill"):
        raise ValueError(action)
    return cli.cmd(action, container)


def logs_cmd(cli: DockerCli, container: str, tail: int = 500, follow: bool = False) -> list[str]:
    return cli.cmd("logs", "--tail", str(tail), *(["-f"] if follow else []), container)


def compose_up_cmd(cli: DockerCli, file: str = "compose.yaml", build: bool = True) -> list[str]:
    return cli.compose_cmd("-f", file, "up", "-d", *(["--build"] if build else []))


def compose_down_cmd(cli: DockerCli, file: str = "compose.yaml", volumes: bool = False) -> list[str]:
    return cli.compose_cmd("-f", file, "down", *(["-v"] if volumes else []))


def find_compose_file(folder) -> str:
    for n in ("compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml"):
        if (Path(folder) / n).is_file():
            return n
    return ""


# ====================================================================== host ports
def port_free(port: int) -> bool:
    """True when nothing listens on the port (a connect test + a bind test: on Windows a bind can succeed
    next to a listener that did not ask for exclusive use)."""
    import socket
    c = socket.socket()
    c.settimeout(0.3)
    try:
        if c.connect_ex(("127.0.0.1", port)) == 0:
            return False
    except OSError:
        pass
    finally:
        c.close()
    for host in ("0.0.0.0", "127.0.0.1"):
        s = socket.socket()
        try:
            s.bind((host, port))
        except OSError:
            return False
        finally:
            s.close()
    return True


def free_port_near(port: int) -> int:
    for p in list(range(port + 1, port + 50)) + [8081, 8888, 18080]:
        if 0 < p < 65536 and port_free(p):
            return p
    return 0


def compose_host_ports(folder, file: str = "compose.yaml") -> list[int]:
    """Host ports published by a compose file (the left number of "HOST:CONTAINER")."""
    text = _read(Path(folder) / file)
    ports = []
    for m in re.finditer(r"^\s*-\s*[\"']?(?:[\d.]+:)?(\d{2,5}):\d{2,5}(?:/\w+)?[\"']?\s*$", text, re.M):
        ports.append(int(m.group(1)))
    return ports


def busy_compose_ports(folder, file: str = "compose.yaml") -> list[int]:
    return [p for p in compose_host_ports(folder, file) if not port_free(p)]


def change_compose_host_port(folder, file: str, old: int, new: int) -> bool:
    path = Path(folder) / file
    text = _read(path)
    new_text, n = re.subn(r"^(\s*-\s*[\"']?(?:[\d.]+:)?)" + str(old) + r"(:\d{2,5})", lambda m: m.group(1) + str(new)
                          + m.group(2), text, flags=re.M)
    if n:
        path.write_text(new_text, encoding="utf-8", newline="\n")
    return bool(n)

