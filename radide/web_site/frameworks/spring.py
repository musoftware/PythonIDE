"""Spring Boot web sites (``spring-web`` plugin) - Spring MVC + Thymeleaf, or a REST API.

- **New Project** downloads a project from **start.spring.io** (Maven, Java 17, dependencies webmvc / thymeleaf /
  devtools) and adds a home controller + pages; offline it writes the same project itself with the Maven
  wrapper bundled in ``spring_wrapper/`` (Apache-2.0, from start.spring.io). Maven is fetched by the wrapper
  into ``~/.m2/wrapper`` - nothing to install.
- **JDK**: ``JAVA_HOME``, then ``java``/``javac`` on PATH, then ``%LOCALAPPDATA%\\Java\\jdk*`` and
  ``%LOCALAPPDATA%\\RADIDE\\tools\\jdk*`` (17 or newer).
- **Run**: ``mvnw spring-boot:run`` with ``SERVER_PORT`` / ``SERVER_ADDRESS`` / ``SPRING_PROFILES_ACTIVE=dev``
  behind the DevServer. The ``dev`` profile serves templates and static files straight from ``src/main/resources``
  (edit + save = live reload, no rebuild); saving a ``.java`` file runs ``mvnw compile`` and **devtools**
  restarts the application.
- **Debug (F5)**: the forked JVM gets ``-agentlib:jdwp=...suspend=y`` and radide/jdwp_engine.py attaches.
- **Routes** from ``@RequestMapping`` / ``@GetMapping`` ...; **IntelliSense** for Thymeleaf view names in
  ``return "`` of controllers, ``redirect:`` paths, ``th:href="@{...}"`` routes and ``~{fragment}`` names.
  Java itself through jdtls when installed (radide/lsp.py ``java``).
"""
from __future__ import annotations

import io
import os
import re
import shutil
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from ..project import SiteTemplate, register_template
from .backend_common import (TOOLS, FrameworkPlugin, Route, Tool, filter_prefix, join_url, line_of, read_text,
                             safe_identifier, string_context, walk_files, which, with_progress, write_files)

WRAPPER_DIR = Path(__file__).resolve().parent / "spring_wrapper"
INITIALIZR = "https://start.spring.io/starter.zip"
BOOT_FALLBACK = "4.2.0"
MAPPING_RE = re.compile(r"@(Get|Post|Put|Patch|Delete|Request)Mapping\s*(\(([^)]*)\))?")


# ============================================================================ JDK
def _java_version(java_home: Path) -> int:
    release = java_home / "release"
    m = re.search(r'JAVA_VERSION="(\d+)', read_text(release)) if release.exists() else None
    if m:
        return int(m.group(1))
    m = re.search(r"jdk-?(\d+)", java_home.name)
    return int(m.group(1)) if m else 0


def find_jdk(minimum: int = 17) -> str:
    """JAVA_HOME of a JDK >= *minimum* ("" when none)."""
    cands: list[Path] = []
    if os.environ.get("JAVA_HOME"):
        cands.append(Path(os.environ["JAVA_HOME"]))
    javac = which("javac")
    if javac:
        cands.append(Path(javac).resolve().parent.parent)
    local = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    for base in (local / "Java", TOOLS, Path(r"C:\Program Files\Java"), Path(r"C:\Program Files\Eclipse Adoptium"),
                 Path(r"C:\Program Files\Microsoft")):
        if base.is_dir():
            cands += sorted((p for p in base.glob("jdk*") if p.is_dir()), reverse=True)
    for c in cands:
        if (c / "bin" / "javac.exe").exists() or (c / "bin" / "javac").exists():
            if _java_version(c) >= minimum or _java_version(c) == 0:
                return str(c)
    return ""


def java_exe() -> str:
    jdk = find_jdk()
    return str(Path(jdk) / "bin" / "java.exe") if jdk else which("java")


def mvnw(folder: Path) -> str:
    f = Path(folder) / ("mvnw.cmd" if os.name == "nt" else "mvnw")
    return str(f) if f.exists() else (which("mvn") or "mvn")


# ============================================================================ templates
def _package(name: str) -> str:
    return "com.example." + safe_identifier(name, "app").lower()


def _download_initializr(folder: Path, name: str, deps: str, log=None, reporter=None) -> bool:
    art = safe_identifier(name, "app").lower()
    q = urllib.parse.urlencode({"type": "maven-project", "language": "java", "baseDir": art, "groupId": "com.example",
                                "artifactId": art, "name": safe_identifier(name), "packageName": _package(name),
                                "packaging": "jar", "javaVersion": "17", "dependencies": deps})
    try:
        req = urllib.request.Request(f"{INITIALIZR}?{q}", headers={"User-Agent": "RAD-IDE"})
        with urllib.request.urlopen(req, timeout=30) as r:
            if reporter is None:
                data = r.read()
            else:                                    # byte progress (Content-Length when the server sends it)
                total = int(r.headers.get("Content-Length") or 0)
                buf = bytearray()
                while True:
                    if reporter.cancelled:
                        return False
                    chunk = r.read(1 << 15)
                    if not chunk:
                        break
                    buf += chunk
                    reporter.bytes(len(buf), total, "start.spring.io")
                data = bytes(buf)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                parts = Path(info.filename).parts
                if len(parts) < 2 or info.is_dir() or ".." in parts:
                    continue
                target = Path(folder, *parts[1:])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(info))
        return True
    except (OSError, zipfile.BadZipFile) as e:
        if log:
            log(f"start.spring.io: {e} - writing the project offline")
        return False


def _offline_project(folder: Path, name: str, thymeleaf: bool) -> None:
    art = safe_identifier(name, "app").lower()
    deps = ["spring-boot-starter-webmvc"] + (["spring-boot-starter-thymeleaf"] if thymeleaf else [])
    dep_xml = "".join(f"""
		<dependency>
			<groupId>org.springframework.boot</groupId>
			<artifactId>{d}</artifactId>
		</dependency>""" for d in deps)
    pom = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
	xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
	<modelVersion>4.0.0</modelVersion>
	<parent>
		<groupId>org.springframework.boot</groupId>
		<artifactId>spring-boot-starter-parent</artifactId>
		<version>{BOOT_FALLBACK}</version>
		<relativePath/>
	</parent>
	<groupId>com.example</groupId>
	<artifactId>{art}</artifactId>
	<version>0.0.1-SNAPSHOT</version>
	<name>{safe_identifier(name)}</name>
	<properties>
		<java.version>17</java.version>
	</properties>
	<dependencies>{dep_xml}
		<dependency>
			<groupId>org.springframework.boot</groupId>
			<artifactId>spring-boot-devtools</artifactId>
			<scope>runtime</scope>
			<optional>true</optional>
		</dependency>
	</dependencies>
	<build>
		<plugins>
			<plugin>
				<groupId>org.springframework.boot</groupId>
				<artifactId>spring-boot-maven-plugin</artifactId>
			</plugin>
		</plugins>
	</build>
</project>
"""
    pkg = _package(name)
    cls = safe_identifier(name) + "Application"
    write_files(folder, {
        "pom.xml": pom,
        f"src/main/java/{pkg.replace('.', '/')}/{cls}.java": f"""package {pkg};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class {cls} {{

	public static void main(String[] args) {{
		SpringApplication.run({cls}.class, args);
	}}

}}
""",
        "src/main/resources/application.properties": f"spring.application.name={art}\n",
        ".gitignore": "target/\n.idea/\n*.iml\n",
    })
    for src, rel in (("mvnw", "mvnw"), ("mvnw.cmd", "mvnw.cmd"),
                     ("maven-wrapper.properties", ".mvn/wrapper/maven-wrapper.properties")):
        target = Path(folder) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() and (WRAPPER_DIR / src).exists():
            shutil.copyfile(WRAPPER_DIR / src, target)


DEV_PROPERTIES = """# dev profile (RAD IDE runs the site with SPRING_PROFILES_ACTIVE=dev):
# templates and static files are read from the sources, so a save shows up at once (live reload)
spring.thymeleaf.cache=false
spring.thymeleaf.prefix=file:src/main/resources/templates/
spring.web.resources.static-locations=file:src/main/resources/static/
spring.web.resources.cache.period=0
spring.devtools.restart.poll-interval=1s
spring.devtools.restart.quiet-period=400ms
"""


def _app_files(folder: Path, name: str, thymeleaf: bool) -> None:
    pkg = _package(name)
    base = f"src/main/java/{pkg.replace('.', '/')}"
    files = {"src/main/resources/application-dev.properties": DEV_PROPERTIES}
    if thymeleaf:
        files.update({
            f"{base}/web/HomeController.java": f"""package {pkg}.web;

import java.util.ArrayList;
import java.util.List;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;

@Controller
public class HomeController {{

	public record Product(int id, String name, double price) {{ }}

	private final List<Product> products = new ArrayList<>(List.of(
			new Product(1, "Keyboard", 25.0), new Product(2, "Mouse", 12.5), new Product(3, "Monitor", 180.0)));

	@GetMapping("/")
	public String index(Model model) {{
		model.addAttribute("title", "{name}");
		return "index";
	}}

	@GetMapping("/products")
	public String products(Model model) {{
		model.addAttribute("products", products);
		return "products/list";
	}}

	@GetMapping("/products/{{id}}")
	public String product(@PathVariable int id, Model model) {{
		model.addAttribute("product", products.stream().filter(p -> p.id() == id).findFirst().orElse(null));
		return "products/details";
	}}

	@PostMapping("/products")
	public String add(@RequestParam String name, @RequestParam(defaultValue = "0") double price) {{
		products.add(new Product(products.size() + 1, name, price));
		return "redirect:/products";
	}}
}}
""",
            f"{base}/web/ApiController.java": f"""package {pkg}.web;

import java.time.Instant;
import java.util.Map;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class ApiController {{

	@GetMapping("/time")
	public Map<String, Object> time() {{
		return Map.of("time", Instant.now().toString(), "app", "{name}");
	}}
}}
""",
            "src/main/resources/templates/fragments/layout.html": f"""<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head th:fragment="head(title)">
	<meta charset="utf-8">
	<title th:text="${{title}}">{name}</title>
	<link rel="stylesheet" th:href="@{{/css/site.css}}">
</head>
<body>
<header th:fragment="header">
	<h1>{name}</h1>
	<nav><a th:href="@{{/}}">Home</a> <a th:href="@{{/products}}">Products</a></nav>
</header>
</body>
</html>
""",
            "src/main/resources/templates/index.html": f"""<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head th:replace="~{{fragments/layout :: head('{name}')}}"></head>
<body>
<header th:replace="~{{fragments/layout :: header}}"></header>
<main>
	<p>Welcome to <strong th:text="${{title}}">{name}</strong> - a Spring Boot app made with RAD IDE.</p>
	<p>Server time: <span id="time">...</span></p>
</main>
<script>fetch('/api/time').then(r => r.json()).then(d => document.getElementById('time').textContent = d.time);</script>
</body>
</html>
""",
            "src/main/resources/templates/products/list.html": """<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head th:replace="~{fragments/layout :: head('Products')}"></head>
<body>
<header th:replace="~{fragments/layout :: header}"></header>
<main>
	<h2>Products</h2>
	<ul>
		<li th:each="p : ${products}"><a th:href="@{/products/{id}(id=${p.id})}" th:text="${p.name}">x</a>
			- <span th:text="${#numbers.formatDecimal(p.price, 1, 2)}">0</span></li>
	</ul>
	<form method="post" th:action="@{/products}">
		<input name="name" placeholder="Name" required> <input name="price" type="number" step="0.01">
		<button>Add</button>
	</form>
</main>
</body>
</html>
""",
            "src/main/resources/templates/products/details.html": """<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head th:replace="~{fragments/layout :: head('Product')}"></head>
<body>
<header th:replace="~{fragments/layout :: header}"></header>
<main th:if="${product != null}">
	<h2 th:text="${product.name}">Name</h2>
	<p>Price: <span th:text="${product.price}">0</span></p>
	<p><a th:href="@{/products}">Back</a></p>
</main>
</body>
</html>
""",
            "src/main/resources/static/css/site.css": """body { font-family: "Segoe UI", system-ui, sans-serif; margin: 0; background: #f5f6f8; color: #222; }
header { background: #3d7a1f; color: #fff; padding: 14px 28px; } header h1 { margin: 0; font-size: 22px; }
nav a { color: #dfffd0; margin-right: 14px; }
main { max-width: 860px; margin: 24px auto; background: #fff; padding: 20px 28px; border-radius: 8px; }
""",
        })
    else:
        files[f"{base}/web/ProductsController.java"] = f"""package {pkg}.web;

import java.util.ArrayList;
import java.util.List;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/products")
public class ProductsController {{

	public record Product(int id, String name, double price) {{ }}

	private final List<Product> products = new ArrayList<>(List.of(new Product(1, "Keyboard", 25.0)));

	@GetMapping
	public List<Product> all() {{
		return products;
	}}

	@GetMapping("/{{id}}")
	public ResponseEntity<Product> one(@PathVariable int id) {{
		return products.stream().filter(p -> p.id() == id).findFirst().map(ResponseEntity::ok)
				.orElse(ResponseEntity.notFound().build());
	}}

	@PostMapping
	public Product add(@RequestBody Product p) {{
		Product n = new Product(products.size() + 1, p.name(), p.price());
		products.add(n);
		return n;
	}}
}}
"""
        files["src/main/resources/static/index.html"] = (f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
                                                         f"<title>{name}</title></head><body><h1>{name}</h1>"
                                                         f"<p>REST API: <a href='/api/products'>/api/products</a></p>"
                                                         f"</body></html>\n")
    write_files(folder, files)
    for f in ("HELP.md",):
        p = Path(folder) / f
        if p.exists():
            p.unlink()


def _creator(thymeleaf: bool):
    def create(folder: Path, name: str) -> dict:
        deps = "webmvc,thymeleaf,devtools" if thymeleaf else "webmvc,devtools"

        def fetch(r):
            return (_download_initializr(folder, name, deps, reporter=r)
                    or (not (r is not None and r.cancelled)
                        and _download_initializr(folder, name, deps.replace("webmvc", "web"), reporter=r)))
        if not with_progress("Downloading the project from start.spring.io", fetch, cancellable=True):
            _offline_project(folder, name, thymeleaf)
        _app_files(folder, name, thymeleaf)
        return {"start": "/", "framework": "spring"}
    return create


register_template(SiteTemplate("spring-mvc", "Spring Boot MVC + Thymeleaf",
                               "A Spring Boot web app from start.spring.io (Maven wrapper, Java 17): controllers, "
                               "Thymeleaf pages with a layout fragment, a form and a JSON route; devtools restart.",
                               ("spring-web",), _creator(True), 10, extra={"framework": "spring"}))
register_template(SiteTemplate("spring-rest", "Spring Boot REST API",
                               "A Spring Boot REST API (@RestController with GET/POST) from start.spring.io.",
                               ("spring-web",), _creator(False), 20, extra={"framework": "spring"}))


# ============================================================================ routes / views
def _mapping_paths(args: str | None) -> list[str]:
    if not args:
        return [""]
    m = re.search(r"(?:value|path)\s*=\s*(\{[^}]*\}|\"[^\"]*\")", args)
    src = m.group(1) if m else args
    if not m and "=" in args and not args.strip().startswith(("\"", "{")):
        return [""]
    found = re.findall(r"\"([^\"]*)\"", src)
    return found or [""]


def _request_method(kind: str, args: str | None) -> str:
    if kind != "Request":
        return kind.upper()
    m = re.search(r"RequestMethod\.(\w+)", args or "")
    return m.group(1) if m else "ANY"


def spring_routes(folder: Path) -> list[Route]:
    out: list[Route] = []
    src = Path(folder) / "src" / "main" / "java"
    for f in walk_files(src if src.is_dir() else Path(folder), (".java", ".kt"), 4000):
        text = read_text(f)
        if "Controller" not in text:
            continue
        cm = re.search(r"\b(class|interface)\s+(\w+)", text)
        if not cm:
            continue
        cls = cm.group(2)
        head = text[:cm.start()]
        if "@Controller" not in head and "@RestController" not in head:
            continue
        prefixes = [""]
        for m in MAPPING_RE.finditer(head):
            if m.group(1) == "Request":
                prefixes = _mapping_paths(m.group(3))
        for m in MAPPING_RE.finditer(text, cm.end()):
            method = _request_method(m.group(1), m.group(3))
            after = text[m.end():m.end() + 400]
            mm = re.search(r"(\w+)\s*\(", re.sub(r"@\w+(\([^)]*\))?", "", after))
            handler = f"{cls}.{mm.group(1)}" if mm else cls
            for pre in prefixes:
                for p in _mapping_paths(m.group(3)):
                    out.append(Route(method, join_url(pre, p) if (pre or p) else "/", handler, str(f),
                                     line_of(text, m.start()), mm.group(1) if mm else ""))
    return sorted(out, key=lambda r: (r.path, r.method))


def template_names(folder: Path) -> list[str]:
    root = Path(folder) / "src" / "main" / "resources" / "templates"
    if not root.is_dir():
        return []
    return sorted(f.relative_to(root).with_suffix("").as_posix() for f in walk_files(root, (".html",), 3000))


def fragment_names(folder: Path) -> list[str]:
    root = Path(folder) / "src" / "main" / "resources" / "templates"
    out = []
    for f in walk_files(root, (".html",), 3000) if root.is_dir() else []:
        name = f.relative_to(root).with_suffix("").as_posix()
        for m in re.finditer(r"th:fragment\s*=\s*\"(\w+)", read_text(f)):
            out.append(f"{name} :: {m.group(1)}")
    return sorted(out)


# ============================================================================ plugin
class SpringPlugin(FrameworkPlugin):
    id = "spring-web"
    display_name = "Spring Boot Web App (Java)"
    framework = "spring"
    framework_title = "Spring Boot"
    cli_title = "Maven (mvnw)"
    code_ext = ".java"
    web_kind = "spring"
    default_template = "spring-mvc"
    interpreter_names = ["java"]
    tool_names = ["JDK 17+"]
    view_ext = (".html",)
    install_hint = "A JDK 17 or newer is needed (JAVA_HOME, PATH or %LOCALAPPDATA%\\Java)."
    keywords = ("abstract assert boolean break byte case catch char class const continue default do double else enum "
                "extends final finally float for goto if implements import instanceof int interface long native new "
                "package private protected public record return short static strictfp super switch synchronized "
                "this throw throws transient try var void volatile while true false null").split()
    builtins = ["String", "List", "Map", "Model", "Controller", "RestController", "GetMapping", "PostMapping",
                "RequestMapping", "PathVariable", "RequestParam", "RequestBody", "ResponseEntity", "Autowired",
                "Service", "Repository", "Component"]
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"']

    def find_interpreter(self, configured: str = "") -> str:
        if configured and Path(configured).exists():
            return configured
        return java_exe()

    def env(self) -> dict:
        jdk = find_jdk()
        env = {"SPRING_PROFILES_ACTIVE": "dev", "SERVER_ADDRESS": "127.0.0.1", "MAVEN_BATCH_MODE": "true"}
        if jdk:
            env["JAVA_HOME"] = jdk
            env["PATH"] = str(Path(jdk) / "bin") + os.pathsep + os.environ.get("PATH", "")
        return env

    def backend(self, server) -> dict:
        env = self.env()
        env["SERVER_PORT"] = "{port}"
        return {"argv": [mvnw(server.folder), "-B", "spring-boot:run"], "cwd": server.folder, "env": env,
                "prepare": [], "timeout": 900, "restart_on_change": False}

    def debug_backend(self, server, jdwp_port: int) -> dict:
        spec = self.backend(server)
        spec["argv"] = spec["argv"] + [
            f"-Dspring-boot.run.jvmArguments=-agentlib:jdwp=transport=dt_socket,server=y,suspend=y,"
            f"address=127.0.0.1:{jdwp_port}"]
        return spec

    def start_debug(self, win, project, path=None):          # radide/web_site/debug.py start()
        return self.debug_website(win, project, path)

    def debug_website(self, win, project, path=None):
        from . import debug_support
        return debug_support.debug_spring(win, self, project, path)

    def compile_argv(self, folder: Path) -> list[str]:
        """Saving a .java file: compile so devtools restarts the running app."""
        return [mvnw(folder), "-B", "-q", "-o", "compile"]

    # ---- tools
    def tool_status(self) -> list[Tool]:
        try:
            from ...lsp import server_command
            jdtls = " ".join(server_command("java") or [])
        except Exception:  # noqa: BLE001
            jdtls = ""
        return [Tool("JDK 17+", find_jdk(), "compile / run", self.install_hint),
                Tool("Maven wrapper", "mvnw.cmd (per project)", "build", "comes with the project"),
                Tool("jdtls", jdtls, "Java IntelliSense (LSP)", "Eclipse JDT Language Server")]

    # ---- CLI
    def cli_presets(self, project) -> list[tuple[str, str]]:
        return [("Compile", "mvnw compile"), ("Package (jar)", "mvnw -DskipTests package"), ("Run tests", "mvnw test"),
                ("Clean", "mvnw clean"), ("Dependency tree", "mvnw dependency:tree"),
                ("Check for updates", "mvnw versions:display-dependency-updates"),
                ("New controller + page", "new controller {name}"),
                ("Build container image", "mvnw spring-boot:build-image")]

    def cli_env(self, project) -> dict:
        return self.env()

    def cli_argv(self, project, command: str) -> list[str]:
        argv = super().cli_argv(project, command)
        if argv and argv[0].lower() in ("mvnw", "mvn", "./mvnw", "mvnw.cmd"):
            argv[0] = mvnw(Path(project.folder))
            if "-B" not in argv:
                argv.insert(1, "-B")
        return argv

    def cli_internal(self, project, command: str, log=print) -> bool:
        m = re.match(r"\s*new\s+controller\s+(\w+)\s*$", command)
        if not m:
            return False
        name = m.group(1)
        folder = Path(project.folder)
        mains = list((folder / "src" / "main" / "java").rglob("*Application.java"))
        if not mains:
            log("*** no @SpringBootApplication class found")
            return True
        pkg_dir = mains[0].parent
        pkg = ".".join(pkg_dir.relative_to(folder / "src" / "main" / "java").parts)
        cls = name[0].upper() + name[1:] + "Controller"
        low = name.lower()
        target = pkg_dir / "web" / f"{cls}.java"
        write_files(folder, {
            target.relative_to(folder).as_posix(): f"""package {pkg}.web;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@Controller
@RequestMapping("/{low}")
public class {cls} {{

	@GetMapping
	public String index(Model model) {{
		model.addAttribute("message", "Hello from {cls}");
		return "{low}/index";
	}}
}}
""",
            f"src/main/resources/templates/{low}/index.html": f"""<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head><meta charset="utf-8"><title>{name}</title></head>
<body><h1>{name}</h1><p th:text="${{message}}">message</p></body>
</html>
"""})
        log(f"created {target.relative_to(folder)} and src/main/resources/templates/{low}/index.html")
        return True

    # ---- routes / views
    def routes(self, project) -> list[Route]:
        return spring_routes(Path(project.folder))

    def view_names(self, project) -> list[str]:
        return template_names(Path(project.folder))

    def completion_items(self, project, path: Path, before: str):
        ext = Path(path).suffix.lower()
        if ext not in (".java", ".kt", ".html"):
            return None
        ctx = string_context(before)
        if ctx is None:
            return None
        head, prefix = ctx
        folder = Path(project.folder)
        if ext in (".java", ".kt"):
            if prefix.startswith("redirect:"):
                return filter_prefix([(f"redirect:{r.url_path()}", "value", f"{r.method} {r.handler}")
                                      for r in self.routes(project) if r.method in ("GET", "ANY")], "")
            if re.search(r"\breturn\s*$|ModelAndView\s*\(\s*$|setViewName\s*\(\s*$", head):
                items = [(v, "file", "templates/" + v + ".html") for v in template_names(folder)]
                items += [("redirect:" + r.url_path(), "value", f"{r.method} {r.handler}") for r in self.routes(project)
                          if r.method in ("GET", "ANY")]
                return filter_prefix(items, prefix)
            return None
        m = re.search(r"th:(?:href|action|src)\s*=\s*$", head)
        if m and prefix.startswith("@{"):
            return filter_prefix([("@{" + r.url_path() + "}", "value", f"{r.method} {r.handler}")
                                  for r in self.routes(project)], "")
        if re.search(r"th:(?:replace|insert|include)\s*=\s*$", head) and prefix.startswith("~{"):
            return [("~{" + f + "}", "file", "fragment") for f in fragment_names(folder)] + \
                   [("~{" + t + "}", "file", "template") for t in template_names(folder)]
        if re.search(r"(?:href|action|src)\s*=\s*$|fetch\(\s*$", head):
            return filter_prefix([(r.url_path(), "value", f"{r.method} {r.handler}") for r in self.routes(project)],
                                 prefix)
        return None


PLUGIN = SpringPlugin()

__all__ = ["PLUGIN", "SpringPlugin", "find_jdk", "fragment_names", "mvnw", "spring_routes", "template_names"]
