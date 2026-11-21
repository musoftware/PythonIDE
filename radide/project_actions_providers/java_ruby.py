"""Project actions for Spring Boot (Maven / Gradle tasks, New Controller / Entity / Repository / Service in the
package folders) and Ruby web apps: Rails (rails generate, db:migrate, routes) and Sinatra."""
from __future__ import annotations

import os
import re
from pathlib import Path

from ..project_actions import Action, Field, Provider, Separator, Submenu, matches, read_text
from ._common import kebab, log_routes, snake, studly, under, write_new

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


RAILS_GENERATORS = [
    # (generator, title, default name, fields label or "", fields placeholder, folder)
    ("controller", "Controller", "Posts", "Actions (space separated)", "index show", "app/controllers"),
    ("model", "Model", "Post", "Attributes (name:type ...)", "title:string body:text published:boolean "
     "user:references", "app/models"),
    ("scaffold", "Scaffold", "Post", "Attributes (name:type ...)", "title:string body:text", "app/controllers"),
    ("resource", "Resource (model + controller + routes)", "Post", "Attributes (name:type ...)", "title:string",
     "app/controllers"),
    ("migration", "Migration", "AddTitleToPosts", "Columns (name:type ...)", "title:string", "db/migrate"),
    ("mailer", "Mailer", "UserMailer", "Methods (space separated)", "welcome", "app/mailers"),
    ("job", "Job", "CleanupJob", "", "", "app/jobs"),
    ("helper", "Helper", "Posts", "", "", "app/helpers"),
    ("channel", "Channel", "Chat", "Actions (space separated)", "speak", "app/channels"),
    ("authentication", "Authentication (Rails 8)", "", "", "", "app/controllers"),
]
GEN_BY_KIND = {g[0]: g for g in RAILS_GENERATORS}
ATTRIBUTE_TYPES = ("string text integer bigint float decimal boolean date datetime time binary references json "
                   "attachment rich_text password digest uuid").split()

RAILS_VIEW = """<h1><%= "{title}" %></h1>

<p>Find me in app/views/{rel}</p>
"""
RAILS_PARTIAL = """<%# Partial: render "{name}" (local variables: pass them as render "{name}", x: value) %>
<div id="<%= "{dom}" %>">
</div>
"""
RAILS_TEST = {
    "model": """require "test_helper"

class {cls}Test < ActiveSupport::TestCase
  test "the truth" do
    assert true
  end
end
""",
    "controller": """require "test_helper"

class {cls}ControllerTest < ActionDispatch::IntegrationTest
  test "should get index" do
    get "/{path}"
    assert_response :success
  end
end
""",
    "integration": """require "test_helper"

class {cls}Test < ActionDispatch::IntegrationTest
  test "can see the home page" do
    get "/"
    assert_response :success
  end
end
""",
}
RSPEC_TEST = """require "rails_helper"

RSpec.describe {cls}, type: :{kind} do
  it "works" do
    expect(true).to be(true)
  end
end
"""
TEST_HELPER = """ENV["RAILS_ENV"] ||= "test"
require_relative "../config/environment"
require "rails/test_help"

module ActiveSupport
  class TestCase
    # Run tests in parallel with specified workers (threads: Windows has no fork)
    parallelize(workers: :number_of_processors, with: :threads)

    # Setup all fixtures in test/fixtures/*.yml for all tests in alphabetical order.
    fixtures :all

    # Add more helper methods to be used by all tests here...
  end
end
"""


def rails_project_ok(ctx) -> bool:
    """The gems are installed (bin/rails can run)."""
    f = ctx.folder
    if not (f / "Gemfile.lock").is_file():
        return False
    cfg = read_text(f / ".bundle" / "config")
    return "vendor/bundle" not in cfg or (f / "vendor" / "bundle").is_dir()


def _site_running(ctx) -> bool:
    srv = getattr(ctx.win, "web_server", None)
    return srv is not None and getattr(srv, "project", None) is ctx.project


class Rails(Provider):
    id, title, priority, icon = "rails", "Rails", 45, ("Rb", "#CC0000")
    markers = ("Gemfile", "config/application.rb", "Gemfile.lock")

    def detect(self, folder, project):
        return (folder / "config" / "application.rb").is_file() and (folder / "Gemfile").is_file()

    # ------------------------------------------------------------ running commands
    def rails(self, ctx, *args, title=None, on_done=None, opens=None):
        return ctx.run_cli([ruby(), "bin/rails", *args], env=ruby_env(ctx.folder), title=title or
                           "rails " + " ".join(str(a) for a in args[:3]), on_done=on_done, opens=opens, stdin="")

    def bundle(self, ctx, *args, title=None, on_done=None):
        return ctx.run_cli([ruby(), "-S", "bundle", *args], env=ruby_env(ctx.folder),
                           title=title or "bundle " + " ".join(args[:3]), on_done=on_done, opens="none", stdin="")

    @staticmethod
    def _after_db(ctx):
        def done(run):
            if run.exit_code == 0:
                _refresh_databases(ctx)
        return done

    # ------------------------------------------------------------ generators
    def gen(self, kind: str, rel_folder: str = "") -> Action:
        g, title, default, flabel, placeholder, _folder = GEN_BY_KIND[kind]
        prefix = ""
        if rel_folder:
            for base in ("app/controllers", "app/models", "app/helpers", "app/mailers", "app/jobs", "app/channels"):
                sub = under(rel_folder, base)
                if sub and sub != "concerns":
                    prefix = sub.replace("\\", "/") + "/"
        ask = []
        if kind != "authentication":
            ask.append(Field("name", "Name", default=prefix + default,
                             help="Admin::Posts or admin/posts makes a namespaced one" if kind != "migration" else
                             "AddXToY / RemoveXFromY / CreateZ name the change: Rails writes the columns for you"))
        if flabel:
            ask.append(Field("fields", flabel, required=False, placeholder=placeholder,
                             help=("types: " + ", ".join(ATTRIBUTE_TYPES) + " - add :index or :uniq "
                                   "(email:string:uniq)") if "Attributes" in flabel or "Columns" in flabel else ""))
        if kind == "model":
            ask.append(Field("migration", "Create a migration (--migration)", "bool", default=True))
        if kind in ("model", "scaffold", "resource", "migration"):
            ask.append(Field("migrate", "Run db:migrate afterwards", "bool", default=kind != "model"))
        if kind == "controller":
            ask.append(Field("skip_routes", "Do not add routes (--skip-routes)", "bool", default=False))

        def run(c, k=kind):
            name = (c.values.get("name") or "").strip()
            argv = ["generate", k] + ([name] if name else []) + (c.values.get("fields") or "").split()
            if k == "model" and not c.values.get("migration", True):
                argv.append("--no-migration")
            if k == "controller" and c.values.get("skip_routes"):
                argv.append("--skip-routes")
            def migrate_after(r, cc=c):
                if r.exit_code == 0:
                    self.rails(cc, "db:migrate", title="rails db:migrate", on_done=self._after_db(cc),
                               opens="none")
            self.rails(c, *argv, title=f"rails generate {k} {name}".rstrip(),
                       on_done=migrate_after if c.values.get("migrate") else None)
        return Action(f"g-{kind}", f"New {title}...", run, ask=ask, enabled=rails_project_ok,
                      tip=f"bin/rails generate {kind} - the new files open in the editor")

    def destroy(self) -> Action:
        kinds = [g[0] for g in RAILS_GENERATORS if g[0] != "authentication"]
        return Action("destroy", "Undo a Generator (rails destroy)...",
                      lambda c: self.rails(c, "destroy", c.values["kind"], c.values["name"].strip(),
                                           title=f"rails destroy {c.values['kind']} {c.values['name']}",
                                           opens="none"),
                      ask=[Field("kind", "Generator", "choice", choices=kinds, default="scaffold"),
                           Field("name", "Name", default="Post")],
                      enabled=rails_project_ok, opens="none", refresh=True)

    def gen_items(self) -> list:
        return [self.gen(k) for k in ("controller", "model", "scaffold", "resource", "migration")] + \
            [Separator()] + [self.gen(k) for k in ("mailer", "job", "helper", "channel", "authentication")] + \
            [Separator(), self.destroy()]

    def new_view(self, ctx, rel_folder: str = "", partial: bool = False) -> Action:
        sub = under(rel_folder, "app/views")
        default = (sub + "/" if sub else "posts/") + ("form" if partial else "index")

        def run(c):
            name = c.values["name"].strip().replace("\\", "/").strip("/")
            for ext in (".html.erb", ".erb"):
                if name.endswith(ext):
                    name = name[:-len(ext)]
            d, _, base = name.rpartition("/")
            fmt = c.values.get("format") or "html"
            fname = ("_" if partial and not base.startswith("_") else "") + base + f".{fmt}.erb"
            rel = "app/views/" + (d + "/" if d else "") + fname
            if partial:
                text = RAILS_PARTIAL.format(name=(d + "/" if d else "") + base.lstrip("_"),
                                            dom=base.lstrip("_").replace("/", "_"))
            else:
                text = RAILS_VIEW.format(title=base.replace("_", " ").title(), rel=rel[len("app/views/"):])
            write_new(c, rel, text)
        return Action("new-partial" if partial else "new-view", "New Partial..." if partial else "New View...",
                      run, ask=[Field("name", "Name", default=default,
                                      help="folder/name - app/views/<folder>/" + ("_" if partial else "") +
                                      "<name>.<format>.erb"),
                                Field("format", "Format", "choice", choices=["html", "turbo_stream", "json", "text"],
                                      default="html")])

    # ------------------------------------------------------------ database
    def db_items(self) -> list:
        def reset(c):
            if c.confirm("db:reset DROPS the database, creates it again from db/schema.rb and runs db/seeds.rb.\n\n"
                         "All data of the development database is lost. Continue?"):
                self.rails(c, "db:reset", on_done=self._after_db(c), opens="none")

        def change(c):
            to = c.values["to"]
            if c.confirm(f"rails db:system:change --to={to} rewrites config/database.yml and the Gemfile for "
                         f"{to}, then runs bundle install.\n\nContinue?"):
                def then(r, cc=c):
                    if r.exit_code == 0:
                        self.bundle(cc, "install", on_done=lambda _r: _after_db_change(cc, to))
                self.rails(c, "db:system:change", f"--to={to}", "--force", title=f"rails db:system:change {to}",
                           on_done=then, opens="none")
        return [Action("migrate", "Migrate (db:migrate)", lambda c: self.rails(c, "db:migrate",
                                                                                 on_done=self._after_db(c)),
                       opens="none", refresh=True, toolbar=True, enabled=rails_project_ok, tip="bin/rails db:migrate"),
                Action("rollback", "Rollback (db:rollback)", lambda c: self.rails(c, "db:rollback",
                                                                                   on_done=self._after_db(c)),
                       opens="none", refresh=True, enabled=rails_project_ok),
                Action("status", "Migration Status (db:migrate:status)",
                       lambda c: self.rails(c, "db:migrate:status"), opens="none", enabled=rails_project_ok),
                Action("seed", "Seed (db:seed)", lambda c: self.rails(c, "db:seed", on_done=self._after_db(c)),
                       opens="none", enabled=rails_project_ok),
                Action("prepare", "Prepare (db:prepare)", lambda c: self.rails(c, "db:prepare",
                                                                                on_done=self._after_db(c)),
                       opens="none", enabled=rails_project_ok, tip="create the database if needed and migrate"),
                Action("reset", "Reset Database (db:reset)...", reset, opens="none", enabled=rails_project_ok),
                Separator(),
                Action("db-system-change", "Change Database System (db:system:change)...", change, opens="none",
                       enabled=rails_project_ok,
                       ask=[Field("to", "Database", "choice", choices=["sqlite3", "mysql", "postgresql", "trilogy"],
                                  default="postgresql")]),
                Action("databases", "Show in Databases", lambda c: _show_databases(c), opens="none")]

    # ------------------------------------------------------------ tests
    def test_items(self, ctx, rel_folder: str = "") -> list:
        rspec = (ctx.folder / "spec").is_dir()
        items = [Action("test", "Run Tests" + (" (rspec)" if rspec else " (bin/rails test)"),
                        lambda c: self.run_tests(c, rel_folder), opens="none", toolbar=False,
                        enabled=rails_project_ok),
                 self.new_test(ctx, rel_folder)]
        if not rspec and not (ctx.folder / "test" / "test_helper.rb").is_file():
            items.insert(0, Action("setup-tests", "Set Up Tests (minitest)", self.setup_tests,
                                   tip="test/test_helper.rb + the test railtie in config/application.rb"))
        return items

    def run_tests(self, ctx, rel_folder: str = ""):
        te = getattr(ctx.win, "test_explorer", None)
        if te is not None and not rel_folder and callable(getattr(te, "run", None)):
            try:
                dock = getattr(ctx.win, "dock_tests", None)
                if dock is not None:
                    dock.show()
                    dock.raise_()
                te.run()
                return
            except Exception:  # noqa: BLE001 - fall back to the command line
                pass
        if (ctx.folder / "spec").is_dir():
            ctx.run_cli([ruby(), "-S", "bundle", "exec", "rspec", *([rel_folder] if rel_folder else [])],
                        env={**ruby_env(ctx.folder), "RAILS_ENV": "test"}, title="rspec", opens="none", stdin="")
        else:
            self.rails(ctx, "test", *([rel_folder] if rel_folder else []), opens="none")

    def setup_tests(self, ctx):
        app = ctx.path("config/application.rb")
        text = read_text(app)
        new = re.sub(r"^#\s*require\s+(['\"])rails/test_unit/railtie\1", 'require "rails/test_unit/railtie"', text,
                     flags=re.M)
        if new != text:
            app.write_text(new, encoding="utf-8", newline="\n")
            ctx.log("config/application.rb: require \"rails/test_unit/railtie\" switched on")
        for d in ("test/models", "test/controllers", "test/integration", "test/fixtures", "test/helpers"):
            ctx.path(d).mkdir(parents=True, exist_ok=True)
        if not ctx.path("test/test_helper.rb").exists():
            write_new(ctx, "test/test_helper.rb", TEST_HELPER)

    def new_test(self, ctx, rel_folder: str = "") -> Action:
        rspec = (ctx.folder / "spec").is_dir()
        sub = under(rel_folder, "spec" if rspec else "test")
        kind_default = {"models": "model", "controllers": "controller", "requests": "request",
                        "integration": "integration"}.get(sub.split("/")[0] if sub else "", "model")
        kinds = ["model", "request", "system"] if rspec else ["model", "controller", "integration"]
        if kind_default not in kinds:
            kind_default = kinds[0]

        def run(c):
            name = c.values["name"].strip()
            kind = c.values["kind"]
            cls = studly(name)
            if rspec:
                folder = {"model": "models", "request": "requests", "system": "system"}[kind]
                write_new(c, f"spec/{folder}/{snake(name)}_spec.rb", RSPEC_TEST.format(cls=cls if kind == "model"
                                                                                       else f'"{cls}"', kind=kind))
                return
            if not c.path("test/test_helper.rb").exists():
                self.setup_tests(c)
            folder = {"model": "models", "controller": "controllers", "integration": "integration"}[kind]
            suffix = "_controller_test.rb" if kind == "controller" else "_test.rb"
            base = snake(name[:-len("Controller")] if kind == "controller" and name.endswith("Controller") else name)
            write_new(c, f"test/{folder}/{base}{suffix}",
                      RAILS_TEST[kind].format(cls=studly(base), path=base))
        return Action("new-test", "New Test...", run,
                      ask=[Field("name", "Name", default="Post" if kind_default == "model" else "Posts"),
                           Field("kind", "Kind", "choice", choices=kinds, default=kind_default)])

    # ------------------------------------------------------------ console / server / misc
    def console(self) -> Action:
        def run(c):
            opener = getattr(c.win, "open_rails_console", None)
            if callable(opener) and opener(c.project):
                return
            c.run_in_terminal([ruby(), "bin/rails", "console"])
        return Action("console", "Console (rails console)", run, opens="none", toolbar=True, enabled=rails_project_ok,
                      tip="Ruby with the application loaded (Rails panel > Console)")

    def server(self) -> Action:
        def run(c):
            if c.project is not None and _website(c):
                try:
                    from ..features.web_workspace import run_website
                    run_website(c.win, c.project)
                    return
                except Exception as e:  # noqa: BLE001
                    c.log(f"*** {e}")
            self.rails(c, "server", opens="none")
        return Action("server", "Server (rails server)", run, toolbar=True, opens="none", icon="SP_MediaPlay",
                      tip="Run the app (the IDE's dev server + Preview; F5 = with the debugger)")

    def debug(self) -> Action:
        def run(c):
            starter = getattr(c.win, "start_or_continue", None)
            if callable(starter):
                starter()
        return Action("debug", "Debug (F5: rails server under rdbg)", run, opens="none",
                      tip="Breakpoints (F9) in controllers, models and views; a request from the Preview stops there")

    def routes(self) -> Action:
        def run(c):
            show = getattr(c.win, "show_rails_routes", None)
            if callable(show) and show(c.project):
                return
            self.rails(c, "routes", opens="none")
        return Action("routes", "Routes", run, opens="none", toolbar=True,
                      tip="bin/rails routes (double-click a route: its controller action)")

    def credentials(self) -> Action:
        def run(c):
            edit = getattr(c.win, "edit_rails_credentials", None)
            if callable(edit):
                edit(c.project, c.folder)
            else:
                c.log("*** the Rails IDE feature is not loaded")
        return Action("credentials", "Edit Credentials (credentials:edit)", run, opens="none",
                      enabled=rails_project_ok,
                      tip="config/credentials.yml.enc decrypted in an editor tab; saving encrypts it again")

    def bundler_items(self) -> list:
        return [Action("bundle", "bundle install", lambda c: self.bundle(c, "install"), opens="none"),
                Action("bundle-update", "bundle update", lambda c: self.bundle(c, "update"), opens="none"),
                Action("bundle-outdated", "bundle outdated", lambda c: self.bundle(c, "outdated"), opens="none"),
                Action("bundle-add", "Add Gem (bundle add)...",
                       lambda c: self.bundle(c, "add", c.values["name"].strip(),
                                             *([f"--group={c.values['group']}"] if c.values["group"] != "default"
                                               else []),
                                             *([f"--version={c.values['version'].strip()}"]
                                               if (c.values.get("version") or "").strip() else []),
                                             title=f"bundle add {c.values['name']}"),
                       ask=[Field("name", "Gem", default="", placeholder="devise"),
                            Field("version", "Version (optional)", required=False, placeholder="~> 4.9"),
                            Field("group", "Group", "choice", choices=["default", "development", "test",
                                                                        "development, test"], default="default")],
                       opens="none")]

    def actions(self, ctx):
        return [self.server(), self.debug(), self.console(),
                Separator(),
                Submenu("Generate", self.gen_items()),
                Submenu("Database", self.db_items()),
                Submenu("Tests", self.test_items(ctx)),
                Submenu("Bundler", self.bundler_items()),
                Separator(),
                self.routes(),
                self.credentials(),
                Action("assets", "Precompile Assets (assets:precompile)",
                       lambda c: self.rails(c, "assets:precompile", opens="none"), opens="none",
                       enabled=rails_project_ok),
                Action("about", "About (rails about)", lambda c: self.rails(c, "about", opens="none"), opens="none",
                       enabled=rails_project_ok),
                Action("notes", "Notes (TODO / FIXME)", lambda c: self.rails(c, "notes", opens="none"),
                       opens="none", enabled=rails_project_ok)]

    def folder_actions(self, ctx, rel_folder):
        if rel_folder == "":
            return self.actions(ctx)
        if matches(rel_folder, "app/models/**"):
            return [self.gen("model", rel_folder), self.gen("scaffold", rel_folder), self.gen("resource", rel_folder)]
        if matches(rel_folder, "app/controllers/**"):
            return [self.gen("controller", rel_folder), self.gen("scaffold", rel_folder),
                    self.gen("resource", rel_folder), self.gen("authentication")]
        if matches(rel_folder, "app/views/**"):
            return [self.new_view(ctx, rel_folder), self.new_view(ctx, rel_folder, partial=True)]
        if matches(rel_folder, "app/helpers/**"):
            return [self.gen("helper", rel_folder)]
        if matches(rel_folder, "app/mailers/**"):
            return [self.gen("mailer", rel_folder)]
        if matches(rel_folder, "app/jobs/**"):
            return [self.gen("job", rel_folder)]
        if matches(rel_folder, "app/channels/**"):
            return [self.gen("channel", rel_folder)]
        if matches(rel_folder, "app"):
            return [self.gen("scaffold"), self.gen("model"), self.gen("controller")]
        if matches(rel_folder, "db/migrate/**", "db"):
            return [self.gen("migration", rel_folder), Separator(), *self.db_items()]
        if matches(rel_folder, "config", "config/credentials"):
            return [self.routes(), self.credentials()]
        if matches(rel_folder, "test/**", "spec/**"):
            return self.test_items(ctx, rel_folder)
        return []

    def file_actions(self, ctx, rel_file):
        if matches(rel_file, "test/**/*_test.rb"):
            return [Action("test-this", "Run This Test File", lambda c: self.rails(c, "test", rel_file,
                                                                                   opens="none"),
                           opens="none", enabled=rails_project_ok)]
        if matches(rel_file, "spec/**/*_spec.rb"):
            return [Action("spec-this", "Run This Spec File",
                           lambda c: c.run_cli([ruby(), "-S", "bundle", "exec", "rspec", rel_file],
                                               env={**ruby_env(c.folder), "RAILS_ENV": "test"}, opens="none",
                                               stdin=""), opens="none", enabled=rails_project_ok)]
        if matches(rel_file, "config/routes.rb"):
            return [self.routes()]
        if matches(rel_file, "db/migrate/*.rb"):
            ver = Path(rel_file).name.split("_", 1)[0]
            if ver.isdigit():
                return [Action("mig-up", "Run This Migration (db:migrate:up)",
                               lambda c: self.rails(c, "db:migrate:up", f"VERSION={ver}", on_done=self._after_db(c),
                                                    opens="none"), opens="none", enabled=rails_project_ok),
                        Action("mig-down", "Revert This Migration (db:migrate:down)",
                               lambda c: self.rails(c, "db:migrate:down", f"VERSION={ver}",
                                                    on_done=self._after_db(c), opens="none"),
                               opens="none", enabled=rails_project_ok)]
        if matches(rel_file, "db/seeds.rb"):
            return [a for a in self.db_items() if isinstance(a, Action) and a.id == "seed"]
        if matches(rel_file, "Gemfile"):
            return self.bundler_items()
        if matches(rel_file, "config/credentials.yml.enc", "config/credentials/*.yml.enc"):
            return [self.credentials()]
        return []


def _website(ctx) -> bool:
    try:
        from ..web_site.project import is_website
        return is_website(ctx.project)
    except Exception:  # noqa: BLE001
        return False


def _refresh_databases(ctx) -> None:
    hook = getattr(ctx.win, "rails_db_changed", None)
    if callable(hook):
        try:
            hook(ctx.project)
        except Exception:  # noqa: BLE001
            pass


def _show_databases(ctx) -> None:
    hook = getattr(ctx.win, "show_rails_database", None)
    if callable(hook):
        hook(ctx.project)


def _after_db_change(ctx, to: str) -> None:
    hook = getattr(ctx.win, "rails_db_system_changed", None)
    if callable(hook):
        hook(ctx.project, to)


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
