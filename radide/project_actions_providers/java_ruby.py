"""Project actions for Spring Boot (Maven / Gradle tasks, New Controller / Entity / Repository / Service in the
package folders) and Ruby web apps: Rails (rails generate, db:migrate, routes) and Sinatra."""
from __future__ import annotations

import os
import re
from pathlib import Path

from ..project_actions import Action, Field, Provider, Separator, Submenu, matches, read_text
from ._common import kebab, log_routes, studly, under, write_new

JAVA_ROOT = "src/main/java"
KOTLIN_ROOT = "src/main/kotlin"


# ============================================================================ Spring Boot
class SpringBoot(Provider):
    id, title, priority, icon = "spring-boot", "Spring Boot", 45, ("Sp", "#6DB33F")
    markers = ("pom.xml", "build.gradle", "build.gradle.kts")

    def detect(self, folder, project):
        if (folder / "pom.xml").is_file() and "spring-boot" in read_text(folder / "pom.xml"):
            return True
        return any((folder / g).is_file() and "org.springframework.boot" in read_text(folder / g)
                   for g in ("build.gradle", "build.gradle.kts"))

    # ---------------------------------------------------------------- build tool
    @staticmethod
    def gradle(folder: Path) -> bool:
        return not (folder / "pom.xml").is_file()

    def tool(self, ctx) -> list[str]:
        f = ctx.folder
        if self.gradle(f):
            w = f / ("gradlew.bat" if os.name == "nt" else "gradlew")
            return [str(w)] if w.exists() else ["gradle"]
        try:
            from ..web_site.frameworks.spring import mvnw
            return [mvnw(f)]
        except Exception:  # noqa: BLE001
            return ["mvn"]

    @staticmethod
    def env() -> dict:
        try:
            from ..web_site.frameworks.spring import find_jdk
            jdk = find_jdk()
        except Exception:  # noqa: BLE001
            jdk = ""
        if not jdk:
            return {}
        return {"JAVA_HOME": jdk, "PATH": os.pathsep.join([str(Path(jdk) / "bin"), os.environ.get("PATH", "")])}

    def task(self, ctx, maven: list[str], gradle: list[str], title: str):
        args = gradle if self.gradle(ctx.folder) else maven
        return ctx.run_cli([*self.tool(ctx), *args], env=self.env(), title=title)

    # ---------------------------------------------------------------- packages
    @staticmethod
    def src_root(folder: Path) -> str:
        return KOTLIN_ROOT if (folder / KOTLIN_ROOT).is_dir() and not (folder / JAVA_ROOT).is_dir() else JAVA_ROOT

    def base_package_dir(self, folder: Path) -> str:
        """The folder (relative) of the @SpringBootApplication class."""
        root = self.src_root(folder)
        for p in sorted((folder / root).rglob("*Application.*")) if (folder / root).is_dir() else []:
            if "@SpringBootApplication" in read_text(p):
                return p.parent.relative_to(folder).as_posix()
        return root

    def package_of(self, folder: Path, rel_dir: str) -> str:
        sub = under(rel_dir, self.src_root(folder))
        return sub.replace("/", ".")

    def new_class(self, kind: str, title: str, default: str, sub: str) -> Action:
        ask = [Field("name", "Name", default=default)]
        if kind == "repository":
            ask.append(Field("entity", "Entity", default="Product"))
        return Action(f"new-{kind}", f"New {title}...", lambda c, k=kind, s=sub: self._new_class(c, k, s), ask=ask)

    def _new_class(self, ctx, kind, sub):
        folder = ctx.folder
        root = self.src_root(folder)
        rel_dir = ""
        if ctx.target is not None:
            t = Path(ctx.target)
            r = ctx.rel(t.parent if t.is_file() else t)
            if matches(r, root + "/**") and r != root:
                rel_dir = r
        if not rel_dir:
            rel_dir = f"{self.base_package_dir(folder)}/{sub}"
        name = studly(ctx.values["name"])
        suffix = {"controller": "Controller", "repository": "Repository", "service": "Service"}.get(kind, "")
        if suffix and not name.endswith(suffix):
            name += suffix
        pkg = self.package_of(folder, rel_dir)
        kotlin = root == KOTLIN_ROOT
        text = (KOTLIN if kotlin else JAVA)[kind].format(
            pkg=pkg, name=name, url=kebab(name[: -len(suffix)] if suffix else name) + ("s" if kind == "controller"
                                                                                     else ""),
            entity=studly(ctx.values.get("entity") or "Item"), persistence=self.persistence(folder),
            base=self.package_of(folder, self.base_package_dir(folder)))
        write_new(ctx, f"{rel_dir}/{name}.{'kt' if kotlin else 'java'}", text)

    @staticmethod
    def persistence(folder: Path) -> str:
        build = read_text(folder / "pom.xml") + read_text(folder / "build.gradle") + read_text(folder /
                                                                                            "build.gradle.kts")
        m = re.search(r"spring-boot-starter-parent</artifactId>\s*<version>(\d+)", build) or \
            re.search(r"org\.springframework\.boot['\"]?\)?\s*version\s*['\"](\d+)", build)
        return "javax.persistence" if m and int(m.group(1)) < 3 else "jakarta.persistence"

    def make_items(self) -> list:
        return [self.new_class("controller", "Controller", "Product", "controller"),
                self.new_class("entity", "Entity", "Product", "model"),
                self.new_class("repository", "Repository", "Product", "repository"),
                self.new_class("service", "Service", "Product", "service")]

    # ---------------------------------------------------------------- menus
    def actions(self, ctx):
        g = self.gradle(ctx.folder)
        return [Action("run", "Run (bootRun)" if g else "Run (spring-boot:run)",
                       lambda c: self.task(c, ["spring-boot:run"], ["bootRun"], "Spring Boot: run"),
                       toolbar=True, opens="none", icon="SP_MediaPlay"),
                Action("package", "Build Jar (skip tests)",
                       lambda c: self.task(c, ["package", "-DskipTests"], ["bootJar", "-x", "test"], "Build jar"),
                       opens="none"),
                Action("test", "Run Tests", lambda c: self.task(c, ["test"], ["test"], "Tests"), opens="none"),
                Action("clean", "Clean", lambda c: self.task(c, ["clean"], ["clean"], "Clean"), opens="none"),
                Action("deps", "Dependency Tree",
                       lambda c: self.task(c, ["dependency:tree"], ["dependencies", "--configuration",
                                                                    "runtimeClasspath"], "Dependencies"),
                       opens="none"),
                Separator(),
                Submenu("Add", self.make_items()),
                Separator(),
                Action("routes", "Show Routes", self._routes, opens="none"),
                Action("open-build", "Open " + ("build.gradle" if g else "pom.xml"),
                       lambda c: c.open_file(c.path("pom.xml") if not g else
                                             (c.path("build.gradle.kts") if c.path("build.gradle.kts").exists()
                                              else c.path("build.gradle"))), opens="none")]

    def _routes(self, ctx):
        from ..web_site.frameworks.spring import spring_routes
        log_routes(ctx, "Spring", spring_routes(ctx.folder))

    def folder_actions(self, ctx, rel_folder):
        if rel_folder == "":
            return self.actions(ctx)
        root = self.src_root(ctx.folder)
        if matches(rel_folder, root + "/**") and rel_folder != root:
            items = self.make_items()
            low = rel_folder.lower()
            order = {"controller": 0, "web": 0, "api": 0, "model": 1, "entity": 1, "domain": 1, "repository": 2,
                     "repo": 2, "service": 3}
            for k, i in order.items():
                if low.endswith("/" + k) or low.endswith("/" + k + "s"):
                    items.insert(0, items.pop(i))
                    break
            return items
        if matches(rel_folder, "src/test/**"):
            return [a for a in self.actions(ctx) if isinstance(a, Action) and a.id == "test"]
        return []

    def file_actions(self, ctx, rel_file):
        if matches(rel_file, "src/test/**/*Test.java", "src/test/**/*Tests.java", "src/test/**/*Test.kt"):
            cls = Path(rel_file).stem
            return [Action("test-this", "Run This Test Class",
                           lambda c: self.task(c, ["test", f"-Dtest={cls}"], ["test", "--tests", f"*{cls}"],
                                               f"Test {cls}"), opens="none")]
        return []


JAVA = {
    "controller": """package {pkg};

import java.util.List;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/{url}")
public class {name} {{

    @GetMapping
    public List<String> list() {{
        return List.of();
    }}

    @GetMapping("/{{id}}")
    public String get(@PathVariable Long id) {{
        return "item " + id;
    }}

    @PostMapping
    public String create(@RequestBody String body) {{
        return body;
    }}
}}
""",
    "entity": """package {pkg};

import {persistence}.Entity;
import {persistence}.GeneratedValue;
import {persistence}.GenerationType;
import {persistence}.Id;

@Entity
public class {name} {{

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;

    public Long getId() {{ return id; }}
    public void setId(Long id) {{ this.id = id; }}
    public String getName() {{ return name; }}
    public void setName(String name) {{ this.name = name; }}
}}
""",
    "repository": """package {pkg};

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

// import {base}.model.{entity};

@Repository
public interface {name} extends JpaRepository<{entity}, Long> {{
}}
""",
    "service": """package {pkg};

import org.springframework.stereotype.Service;

@Service
public class {name} {{
}}
""",
}
KOTLIN = {
    "controller": """package {pkg}

import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/{url}")
class {name} {{

    @GetMapping
    fun list(): List<String> = listOf()

    @GetMapping("/{{id}}")
    fun get(@PathVariable id: Long): String = "item $id"
}}
""",
    "entity": """package {pkg}

import {persistence}.*

@Entity
class {name}(
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null,
    var name: String = "",
)
""",
    "repository": """package {pkg}

import org.springframework.data.jpa.repository.JpaRepository

interface {name} : JpaRepository<{entity}, Long>
""",
    "service": """package {pkg}

import org.springframework.stereotype.Service

@Service
class {name}
""",
}


# ============================================================================ Ruby: Rails / Sinatra
def ruby() -> str:
    try:
        from ..web_site.frameworks.rails import ruby_exe
        r = ruby_exe()
        if r:
            return r
    except Exception:  # noqa: BLE001
        pass
    try:
        from ..lsp_servers import find_ruby
        return find_ruby() or "ruby"
    except Exception:  # noqa: BLE001
        return "ruby"


def ruby_env(folder: Path) -> dict:
    try:
        from ..web_site.frameworks.rails import ruby_env as env
        return env(folder)
    except Exception:  # noqa: BLE001
        return {}


class Rails(Provider):
    id, title, priority, icon = "rails", "Rails", 45, ("Rb", "#CC0000")
    markers = ("Gemfile", "config/application.rb")

    def detect(self, folder, project):
        return (folder / "config" / "application.rb").is_file() and (folder / "Gemfile").is_file()

    def rails(self, ctx, *args, title=None, **kw):
        return ctx.run_cli([ruby(), "bin/rails", *args], env=ruby_env(ctx.folder), title=title or
                           "rails " + " ".join(args[:3]), **kw)

    def gen(self, kind: str, title: str, default: str, fields=True) -> Action:
        ask = [Field("name", "Name", default=default)]
        if fields:
            ask.append(Field("fields", "Fields (name:type ...)", required=False,
                             placeholder="title:string body:text published:boolean"))
        if kind == "controller":
            ask = [Field("name", "Name", default=default),
                   Field("fields", "Actions (space separated)", required=False, placeholder="index show")]
        return Action(f"g-{kind}", f"New {title}...",
                      lambda c, k=kind: self.rails(c, "generate", k, c.values["name"].strip(),
                                                   *(c.values.get("fields") or "").split(),
                                                   title=f"rails g {k} {c.values['name']}"), ask=ask)

    def gen_items(self) -> list:
        return [self.gen("model", "Model", "Post"), self.gen("controller", "Controller", "Posts"),
                self.gen("migration", "Migration", "AddTitleToPosts"), self.gen("scaffold", "Scaffold", "Post"),
                self.gen("mailer", "Mailer", "UserMailer", fields=False), self.gen("job", "Job", "CleanupJob",
                                                                                   fields=False)]

    def db_items(self) -> list:
        return [Action("migrate", "Migrate (db:migrate)", lambda c: self.rails(c, "db:migrate"), opens="none",
                       refresh=True),
                Action("rollback", "Rollback (db:rollback)", lambda c: self.rails(c, "db:rollback"), opens="none",
                       refresh=True),
                Action("status", "Migration Status", lambda c: self.rails(c, "db:migrate:status"), opens="none"),
                Action("seed", "Seed (db:seed)", lambda c: self.rails(c, "db:seed"), opens="none"),
                Action("reset", "Reset Database (db:reset)", lambda c: c.confirm("Drop and recreate the database?")
                       and self.rails(c, "db:reset"), opens="none")]

    def actions(self, ctx):
        return [Action("server", "Server (rails server)", lambda c: self.rails(c, "server"), toolbar=True,
                       opens="none", icon="SP_MediaPlay"),
                Action("console", "Console (rails console)",
                       lambda c: c.run_in_terminal([ruby(), "bin/rails", "console"]), opens="none"),
                Separator(),
                Submenu("Generate", self.gen_items()),
                Submenu("Database", self.db_items()),
                Separator(),
                Action("routes", "Routes (rails routes)", lambda c: self.rails(c, "routes"), opens="none"),
                Action("test", "Run Tests", lambda c: self.rails(c, "test"), opens="none"),
                Action("bundle", "bundle install", lambda c: c.run_cli([ruby(), "-S", "bundle", "install"],
                                                                      env=ruby_env(c.folder)), opens="none")]

    def folder_actions(self, ctx, rel_folder):
        if rel_folder == "":
            return self.actions(ctx)
        if matches(rel_folder, "app/models/**"):
            return [self.gen("model", "Model", "Post"), self.gen("scaffold", "Scaffold", "Post")]
        if matches(rel_folder, "app/controllers/**"):
            return [self.gen("controller", "Controller", "Posts"), self.gen("scaffold", "Scaffold", "Post")]
        if matches(rel_folder, "db/migrate/**", "db"):
            return [self.gen("migration", "Migration", "AddTitleToPosts"), Separator(), *self.db_items()]
        if matches(rel_folder, "config"):
            return [a for a in self.actions(ctx) if isinstance(a, Action) and a.id == "routes"]
        if matches(rel_folder, "test/**", "spec/**"):
            return [a for a in self.actions(ctx) if isinstance(a, Action) and a.id == "test"]
        return []

    def file_actions(self, ctx, rel_file):
        if matches(rel_file, "test/**/*_test.rb"):
            return [Action("test-this", "Run This Test", lambda c: self.rails(c, "test", rel_file), opens="none")]
        if matches(rel_file, "config/routes.rb"):
            return [a for a in self.actions(ctx) if isinstance(a, Action) and a.id == "routes"]
        return []


SINATRA_ROUTE = """# {name} routes - require_relative "routes/{file}" in app.rb

get "/{url}" do
  "{name}"
end

post "/{url}" do
  status 201
end
"""


class Sinatra(Provider):
    id, title, priority, icon = "sinatra", "Sinatra", 40, ("Sn", "#888888")
    markers = ("Gemfile",)

    def detect(self, folder, project):
        return (folder / "Gemfile").is_file() and "sinatra" in read_text(folder / "Gemfile") and \
            not (folder / "config" / "application.rb").is_file()

    @staticmethod
    def main(ctx) -> str:
        for rel in ("app.rb", "server.rb", "main.rb", "config.ru"):
            if ctx.path(rel).is_file():
                return rel
        return "app.rb"

    def actions(self, ctx):
        main = self.main(ctx)
        argv = ([ruby(), "-S", "bundle", "exec", "rackup"] if main == "config.ru"
                else [ruby(), "-S", "bundle", "exec", "ruby", main])
        return [Action("run", f"Run ({main})", lambda c: c.run_cli(argv, env=ruby_env(c.folder)), toolbar=True,
                       opens="none", icon="SP_MediaPlay"),
                Action("bundle", "bundle install", lambda c: c.run_cli([ruby(), "-S", "bundle", "install"],
                                                                      env=ruby_env(c.folder)), opens="none"),
                Separator(),
                Action("new-route", "New Route File...", self._new_route, ask=[Field("name", "Name", default="users")]),
                Action("routes", "Show Routes", self._routes, opens="none")]

    def _new_route(self, ctx):
        name = ctx.values["name"].strip()
        write_new(ctx, f"routes/{kebab(name).replace('-', '_')}.rb",
                  SINATRA_ROUTE.format(name=name, file=kebab(name).replace("-", "_"), url=kebab(name)))

    def _routes(self, ctx):
        from ..web_site.frameworks.rails import parse_sinatra_routes
        log_routes(ctx, "Sinatra", parse_sinatra_routes(ctx.folder))

    def folder_actions(self, ctx, rel_folder):
        return self.actions(ctx) if rel_folder in ("", "routes") else []


PROVIDERS = [SpringBoot(), Rails(), Sinatra()]
