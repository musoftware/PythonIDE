"""Project actions for JavaScript / TypeScript projects: Node package maintenance (on top of the generic npm
scripts provider), NestJS (nest g ...), Angular (ng generate ...), Vite apps (React / Vue / Svelte component
files), Express (route files) and Expo / React Native."""
from __future__ import annotations

import os

from ..project_actions import Action, Field, Provider, Separator, Submenu, matches, package_json
from ._common import (has_dep, has_script, kebab, log_routes, pm, run_script_or, studly, target_folder, under, which,
                      write_new)
from .generic import NodeScripts


# ============================================================================ Node: npm scripts + maintenance
class NodeScriptsPlus(NodeScripts):
    """The generic npm-scripts provider (same id, so it replaces it) plus a Packages sub menu: update,
    outdated, audit, npm-check-updates."""

    def packages_menu(self, folder) -> Submenu:
        m = self.manager(folder)
        upd = {"npm": "update", "yarn": "upgrade", "pnpm": "update", "bun": "update"}[m]
        audit_fix = {"npm": ["npm", "audit", "fix"], "pnpm": ["pnpm", "audit", "--fix"]}.get(m)
        items = [Action("update", f"{m} {upd}", lambda c: c.run_cli([m, upd]), opens="none", refresh=True,
                        tip="Update the packages within the ranges of package.json"),
                 Action("outdated", f"{m} outdated", lambda c: c.run_cli([m, "outdated"]), opens="none",
                        tip="List the packages that have newer versions"),
                 Action("audit", f"{m} audit", lambda c: c.run_cli([m, "audit"]), opens="none",
                        tip="Look for known vulnerabilities")]
        if audit_fix:
            items.append(Action("audit-fix", " ".join(audit_fix), lambda c: c.run_cli(audit_fix), opens="none",
                                refresh=True))
        items += [Separator(),
                  Action("ncu", "Check for Major Updates (npx npm-check-updates)",
                         lambda c: c.run_cli(["npx", "-y", "npm-check-updates"], title="npm-check-updates"),
                         opens="none"),
                  Action("ncu-u", "Upgrade package.json to the Latest Versions (ncu -u)", self._ncu_upgrade,
                         opens="none", refresh=True),
                  Separator(),
                  Action("ci", "Clean Install (npm ci)", lambda c: c.run_cli(["npm", "ci"]), opens="none",
                         refresh=True, enabled=lambda c: (c.folder / "package-lock.json").is_file())]
        return Submenu("Packages", items)

    def _ncu_upgrade(self, ctx):
        if not ctx.confirm("Rewrite package.json with the latest versions of every dependency (npx "
                           "npm-check-updates -u), then install them?"):
            return
        m = self.manager(ctx.folder)
        ctx.run_cli(["npx", "-y", "npm-check-updates", "-u"], title="npm-check-updates -u",
                    on_done=lambda r: r.exit_code == 0 and ctx.run_cli([m, "install"], title=f"{m} install"))

    def actions(self, ctx):
        items = super().actions(ctx)
        return [*items[:-1], self.packages_menu(ctx.folder), items[-1]]

    def folder_actions(self, ctx, rel_folder):
        out = super().folder_actions(ctx, rel_folder)
        return [*out, self.packages_menu(ctx.folder)] if rel_folder == "" else out


# ============================================================================ NestJS
NEST_KINDS = (("module", "Module"), ("controller", "Controller"), ("service", "Service"), ("resource", "Resource"),
              ("gateway", "Gateway"), ("guard", "Guard"), ("interceptor", "Interceptor"), ("pipe", "Pipe"),
              ("middleware", "Middleware"), ("filter", "Filter"), ("class", "Class"), ("interface", "Interface"))


class NestJS(Provider):
    id, title, priority, icon = "nestjs", "NestJS", 45, ("Ne", "#E0234E")
    markers = ("package.json", "nest-cli.json")

    def detect(self, folder, project):
        return has_dep(folder, "@nestjs/core")

    @staticmethod
    def nest(ctx) -> list[str]:
        try:
            from ..web_site.frameworks.nestjs import nest_cli
            js = nest_cli(ctx.folder)
        except Exception:  # noqa: BLE001
            js = ""
        if js:
            return ["node", js]
        if (ctx.folder / "node_modules" / ".bin" / "nest.cmd").exists() or (ctx.folder / "node_modules" / ".bin"
                                                                                / "nest").exists():
            return ["nest"]
        return ["npx", "-y", "@nestjs/cli"]

    def generate(self, kind: str, title: str, default: str) -> Action:
        ask = [Field("name", "Name", default=default),
               Field("flat", "Flat (no own folder, --flat)", "bool"),
               Field("nospec", "Without a test file (--no-spec)", "bool")]
        if kind == "resource":
            ask = [Field("name", "Name", default=default),
                   Field("type", "Transport layer", "choice", default="rest",
                         choices=("rest", "graphql-code-first", "graphql-schema-first", "microservice", "ws")),
                   Field("crud", "Generate CRUD entry points (--crud)", "bool", default=True),
                   Field("nospec", "Without test files (--no-spec)", "bool")]
        return Action(f"g-{kind}", f"New {title}...", lambda c, k=kind: self._generate(c, k), ask=ask,
                      group="generate")

    def _generate(self, ctx, kind):
        name = ctx.values["name"].strip().replace("\\", "/")
        sub = under(target_folder(ctx, "src"), "src")
        if sub and "/" not in name:
            name = f"{sub}/{name}"
        argv = [*self.nest(ctx), "g", kind, name]
        if kind == "resource":
            argv += ["--type", ctx.values.get("type") or "rest"]
            argv.append("--crud" if ctx.values.get("crud") else "--no-crud")
        elif ctx.values.get("flat"):
            argv.append("--flat")
        if ctx.values.get("nospec"):
            argv.append("--no-spec")
        ctx.run_cli(argv, title=f"nest g {kind} {name}")

    def make_menu(self) -> list:
        return [self.generate(k, t, {"module": "users", "resource": "users"}.get(k, "users"))
                for k, t in NEST_KINDS]

    def actions(self, ctx):
        nest = self.nest(ctx)
        return [Action("dev", "Start (watch mode)",
                       lambda c: run_script_or(c, "start:dev", [*nest, "start", "--watch"]),
                       toolbar=True, opens="none", icon="SP_MediaPlay"),
                Action("debug", "Start (debug, watch)", lambda c: run_script_or(c, "start:debug",
                                                                               [*nest, "start", "--debug", "--watch"]),
                       opens="none"),
                Action("build", "Build", lambda c: run_script_or(c, "build", [*nest, "build"]), opens="none"),
                Separator(),
                Submenu("Generate", self.make_menu()),
                Separator(),
                Action("test", "Run Tests", lambda c: run_script_or(c, "test", ["npx", "jest"]), opens="none"),
                Action("test-e2e", "Run e2e Tests", lambda c: run_script_or(c, "test:e2e", ["npx", "jest",
                       "--config", "./test/jest-e2e.json"]), opens="none"),
                Action("lint", "Lint", lambda c: run_script_or(c, "lint", ["npx", "eslint", "src"]), opens="none"),
                Separator(),
                Action("info", "nest info", lambda c: c.run_cli([*nest, "info"]), opens="none"),
                Action("routes", "Show Routes", self._routes, opens="none")]

    def _routes(self, ctx):
        from ..web_site.frameworks.nestjs import nest_routes
        log_routes(ctx, "NestJS", nest_routes(ctx.folder))

    def folder_actions(self, ctx, rel_folder):
        if rel_folder == "":
            return self.actions(ctx)
        if matches(rel_folder, "src/**"):
            return [self.generate("module", "Module", "users"), self.generate("controller", "Controller", "users"),
                    self.generate("service", "Service", "users"), self.generate("resource", "Resource", "users"),
                    Submenu("More", [self.generate(k, t, "users") for k, t in NEST_KINDS[4:]])]
        if matches(rel_folder, "test/**"):
            return [a for a in self.actions(ctx) if isinstance(a, Action) and a.id.startswith("test")]
        return []

    def file_actions(self, ctx, rel_file):
        if matches(rel_file, "**/*.spec.ts", "**/*.e2e-spec.ts"):
            return [Action("test-this", "Run This Test File",
                           lambda c: c.run_cli(["npx", "jest", rel_file], title=f"jest {rel_file}"), opens="none")]
        return []


# ============================================================================ Angular
NG_KINDS = (("component", "Component", "hello"), ("service", "Service", "data"), ("module", "Module", "shared"),
            ("directive", "Directive", "highlight"), ("pipe", "Pipe", "format"), ("guard", "Guard", "auth"),
            ("interface", "Interface", "user"), ("class", "Class", "model"), ("enum", "Enum", "status"),
            ("resolver", "Resolver", "data"), ("interceptor", "Interceptor", "auth"))


class Angular(Provider):
    id, title, priority, icon = "angular", "Angular", 45, ("Ng", "#DD0031")
    markers = ("angular.json", "package.json")

    def detect(self, folder, project):
        return (folder / "angular.json").is_file()

    @staticmethod
    def ng(ctx) -> list[str]:
        b = ctx.folder / "node_modules" / ".bin"
        if (b / "ng.cmd").exists() or (b / "ng").exists():
            return ["ng"]
        return ["npx", "-y", "@angular/cli"]

    def generate(self, kind, title, default) -> Action:
        ask = [Field("name", "Name", default=default)]
        if kind == "component":
            ask += [Field("standalone", "Standalone component", "bool", default=True),
                    Field("inline", "Inline template and styles (-t -s)", "bool"),
                    Field("skip_tests", "Without a test file (--skip-tests)", "bool")]
        elif kind not in ("interface", "enum"):
            ask += [Field("skip_tests", "Without a test file (--skip-tests)", "bool")]
        return Action(f"g-{kind}", f"New {title}...", lambda c, k=kind: self._generate(c, k), ask=ask)

    def _generate(self, ctx, kind):
        name = ctx.values["name"].strip().replace("\\", "/")
        sub = under(target_folder(ctx, "src/app"), "src/app")
        if sub and "/" not in name:
            name = f"{sub}/{name}"
        argv = [*self.ng(ctx), "generate", kind, name]
        if kind == "component":
            argv.append(f"--standalone={'true' if ctx.values.get('standalone') else 'false'}")
            if ctx.values.get("inline"):
                argv += ["--inline-template", "--inline-style"]
        if ctx.values.get("skip_tests"):
            argv.append("--skip-tests")
        ctx.run_cli(argv, title=f"ng generate {kind} {name}")

    def actions(self, ctx):
        ng = self.ng(ctx)
        return [Action("serve", "Serve (ng serve)", lambda c: c.run_cli([*ng, "serve"]), opens="none",
                       toolbar=True, icon="SP_MediaPlay"),
                Action("build", "Build (ng build)", lambda c: c.run_cli([*ng, "build"]), opens="none"),
                Action("build-prod", "Build Production", lambda c: c.run_cli([*ng, "build", "--configuration",
                                                                            "production"]), opens="none"),
                Separator(),
                Submenu("Generate", [self.generate(*k) for k in NG_KINDS]),
                Separator(),
                Action("test", "Run Tests (ng test)", lambda c: c.run_cli([*ng, "test", "--watch=false"]),
                       opens="none"),
                Action("lint", "Lint (ng lint)", lambda c: c.run_cli([*ng, "lint"]), opens="none"),
                Separator(),
                Action("add", "Add Library (ng add)...", lambda c: c.run_cli([*ng, "add", c.values["package"],
                                                                             "--skip-confirmation"]),
                       ask=[Field("package", "Package", placeholder="@angular/material")], opens="none",
                       refresh=True),
                Action("update", "Check for Updates (ng update)", lambda c: c.run_cli([*ng, "update"]), opens="none"),
                Action("version", "ng version", lambda c: c.run_cli([*ng, "version"]), opens="none")]

    def folder_actions(self, ctx, rel_folder):
        if rel_folder == "":
            return self.actions(ctx)
        if matches(rel_folder, "src/app/**", "projects/**"):
            return [self.generate(*NG_KINDS[0]), self.generate(*NG_KINDS[1]), self.generate(*NG_KINDS[2]),
                    Submenu("More", [self.generate(*k) for k in NG_KINDS[3:]])]
        return []


# ============================================================================ Vite apps: React / Vue / Svelte
REACT_TSX = """{css_import}type {name}Props = {{
  title?: string;
}};

export default function {name}({{ title = "{name}" }}: {name}Props) {{
  return (
    <div className="{kebab}">
      <h2>{{title}}</h2>
    </div>
  );
}}
"""
REACT_JSX = """{css_import}export default function {name}({{ title = "{name}" }}) {{
  return (
    <div className="{kebab}">
      <h2>{{title}}</h2>
    </div>
  );
}}
"""
VUE_SFC = """<script setup{lang}>
{props}
</script>

<template>
  <div class="{kebab}">
    <h2>{{{{ title }}}}</h2>
  </div>
</template>

<style scoped>
.{kebab} {{
}}
</style>
"""
SVELTE = """<script{lang}>
  export let title{type} = "{name}";
</script>

<div class="{kebab}">
  <h2>{{title}}</h2>
</div>

<style>
  .{kebab} {{
  }}
</style>
"""


class ViteApp(Provider):
    """One instance per UI library (title "React", "Vue", "Svelte")."""
    priority, markers = 40, ("package.json", "tsconfig.json")

    def __init__(self, lib: str, title: str, icon, dep: str):
        self.lib, self.id, self.title, self.icon, self.dep = lib, f"vite-{lib}", title, icon, dep

    def detect(self, folder, project):
        if not has_dep(folder, self.dep) or has_dep(folder, "next", "nuxt", "@sveltejs/kit", "expo",
                                                     "react-native", "@nestjs/core"):
            return False
        return has_dep(folder, "vite", "react-scripts", "@vue/cli-service") or (folder / "vite.config.js").is_file() \
            or (folder / "vite.config.ts").is_file()

    def ts(self, ctx) -> bool:
        return (ctx.folder / "tsconfig.json").is_file()

    def new_component(self, default_folder="src/components") -> Action:
        ask = [Field("name", "Name", default="MyComponent")]
        if self.lib == "react":
            ask.append(Field("css", "With a CSS file", "bool"))
        return Action("new-component", "New Component...", lambda c: self._new_component(c, default_folder), ask=ask,
                      tip="A component file from a template (the right-clicked folder, else src/components)")

    def _new_component(self, ctx, default_folder):
        name = studly(ctx.values["name"])
        folder = target_folder(ctx, default_folder)
        ts = self.ts(ctx)
        kb = kebab(name)
        if self.lib == "react":
            css = f'import "./{name}.css";\n\n' if ctx.values.get("css") else ""
            if css:
                write_new(ctx, f"{folder}/{name}.css", f".{kb} {{\n}}\n")
            text = (REACT_TSX if ts else REACT_JSX).format(name=name, kebab=kb, css_import=css)
            write_new(ctx, f"{folder}/{name}.{'tsx' if ts else 'jsx'}", text)
        elif self.lib == "vue":
            props = ('defineProps<{ title?: string }>()' if ts
                     else 'defineProps({ title: { type: String, default: "" } })')
            write_new(ctx, f"{folder}/{name}.vue",
                      VUE_SFC.format(lang=' lang="ts"' if ts else "", props=props, kebab=kb))
        else:
            write_new(ctx, f"{folder}/{name}.svelte",
                      SVELTE.format(lang=' lang="ts"' if ts else "", type=": string" if ts else "", name=name,
                                    kebab=kb))

    def actions(self, ctx):
        m = pm(ctx.folder)
        return [Action("dev", "Start Dev Server", lambda c: run_script_or(c, "dev", ["npx", "vite"]), toolbar=True,
                       opens="none", icon="SP_MediaPlay"),
                Action("build", "Build", lambda c: run_script_or(c, "build", ["npx", "vite", "build"]), opens="none"),
                Action("preview", "Preview the Build", lambda c: run_script_or(c, "preview", ["npx", "vite", "preview"]),
                       opens="none"),
                Separator(),
                self.new_component(),
                Separator(),
                Action("test", "Run Tests", lambda c: run_script_or(c, "test", ["npx", "vitest", "run"]), opens="none",
                       enabled=lambda c: has_script(c.folder, "test") or has_dep(c.folder, "vitest")),
                Action("lint", "Lint", lambda c: c.run_cli([m, "run", "lint"]), opens="none",
                       enabled=lambda c: has_script(c.folder, "lint"))]

    def folder_actions(self, ctx, rel_folder):
        if rel_folder == "":
            return self.actions(ctx)
        if matches(rel_folder, "src/**"):
            return [self.new_component()]
        return []


# ============================================================================ Express
ROUTE_CJS = """const express = require("express");

const router = express.Router();

// GET /{url}
router.get("/", (req, res) => {{
  res.json([]);
}});

// GET /{url}/:id
router.get("/:id", (req, res) => {{
  res.json({{ id: req.params.id }});
}});

// POST /{url}
router.post("/", (req, res) => {{
  res.status(201).json(req.body);
}});

module.exports = router;

// in app.js:  app.use("/{url}", require("./{require_path}"));
"""
ROUTE_ESM = """import {{ Router }} from "express";

const router = Router();

// GET /{url}
router.get("/", (req, res) => {{
  res.json([]);
}});

// GET /{url}/:id
router.get("/:id", (req, res) => {{
  res.json({{ id: req.params.id }});
}});

// POST /{url}
router.post("/", (req, res) => {{
  res.status(201).json(req.body);
}});

export default router;

// in app.js:  import {var}Router from "./{require_path}.js";  app.use("/{url}", {var}Router);
"""


class Express(Provider):
    id, title, priority, icon = "express", "Express", 35, ("Ex", "#444444")
    markers = ("package.json",)

    def detect(self, folder, project):
        return has_dep(folder, "express") and not has_dep(folder, "@nestjs/core")

    def routes_dir(self, ctx) -> str:
        for rel in ("src/routes", "routes", "src/api/routes"):
            if ctx.path(rel).is_dir():
                return rel
        return "src/routes" if ctx.path("src").is_dir() else "routes"

    def entry(self, ctx) -> str:
        main = str(package_json(ctx.folder).get("main") or "")
        for rel in (main, "app.js", "server.js", "index.js", "src/app.js", "src/server.js", "src/index.js",
                    "bin/www"):
            if rel and ctx.path(rel).is_file():
                return rel
        return main or "index.js"

    def new_route(self) -> Action:
        return Action("new-route", "New Route File...", self._new_route,
                      ask=[Field("name", "Name (URL path)", default="users")])

    def _new_route(self, ctx):
        name = kebab(ctx.values["name"]) or "items"
        folder = target_folder(ctx, self.routes_dir(ctx))
        esm = package_json(ctx.folder).get("type") == "module"
        ts = (ctx.folder / "tsconfig.json").is_file()
        ext = "ts" if ts else "js"
        text = (ROUTE_ESM if (esm or ts) else ROUTE_CJS).format(url=name, require_path=f"{folder}/{name}",
                                                                var=studly(name)[:1].lower() + studly(name)[1:])
        write_new(ctx, f"{folder}/{name}.{ext}", text)

    def actions(self, ctx):
        entry = self.entry(ctx)
        return [Action("start", "Start", lambda c: run_script_or(c, "start", ["node", entry]), toolbar=True,
                       opens="none", icon="SP_MediaPlay"),
                Action("dev", "Start with Auto Reload (node --watch)",
                       lambda c: run_script_or(c, "dev", ["node", "--watch", entry]), opens="none"),
                Separator(),
                self.new_route()]

    def folder_actions(self, ctx, rel_folder):
        if rel_folder == "":
            return self.actions(ctx)
        if matches(rel_folder, "routes/**", "src/routes/**", "src/api/**", "api/**"):
            return [self.new_route()]
        return []


# ============================================================================ Expo / React Native
class Expo(Provider):
    id, title, priority, icon = "expo", "Expo", 45, ("Ex", "#000020")
    markers = ("package.json", "app.json", "eas.json")

    def detect(self, folder, project):
        return has_dep(folder, "expo")

    def actions(self, ctx):
        eas_ok = lambda c: bool(which("eas", "eas.cmd")) or (c.folder / "node_modules" / ".bin" / "eas.cmd").exists()  # noqa: E731
        return [Action("start", "Start (expo start)", lambda c: c.run_cli(["npx", "expo", "start"]), toolbar=True,
                       opens="none", icon="SP_MediaPlay"),
                Action("web", "Start in the Browser (--web)", lambda c: c.run_cli(["npx", "expo", "start", "--web"]),
                       opens="none"),
                Action("android", "Run on Android (--android)",
                       lambda c: c.run_cli(["npx", "expo", "start", "--android"]), opens="none"),
                Separator(),
                Action("install", "Add Package (expo install)...",
                       lambda c: c.run_cli(["npx", "expo", "install", *c.values["package"].split()]),
                       ask=[Field("package", "Package", placeholder="expo-camera")], opens="none", refresh=True),
                Action("doctor", "Check the Project (expo-doctor)", lambda c: c.run_cli(["npx", "-y", "expo-doctor"]),
                       opens="none"),
                Action("fix", "Fix Package Versions (expo install --fix)",
                       lambda c: c.run_cli(["npx", "expo", "install", "--fix"]), opens="none", refresh=True),
                Separator(),
                Action("prebuild", "Prebuild Native Folders (expo prebuild)",
                       lambda c: c.run_cli(["npx", "expo", "prebuild"]), opens="none", refresh=True),
                Action("export-web", "Export for the Web (expo export)",
                       lambda c: c.run_cli(["npx", "expo", "export", "--platform", "web"]), opens="none"),
                Submenu("EAS Build", [
                    Action("eas-android", "Build Android (eas build -p android)",
                           lambda c: c.run_cli(["eas", "build", "-p", "android"]), opens="none", enabled=eas_ok),
                    Action("eas-ios", "Build iOS (eas build -p ios)",
                           lambda c: c.run_cli(["eas", "build", "-p", "ios"]), opens="none", enabled=eas_ok),
                    Action("eas-install", "Install EAS CLI (npm i -g eas-cli)",
                           lambda c: c.run_cli(["npm", "install", "-g", "eas-cli"]), opens="none")])]

    def folder_actions(self, ctx, rel_folder):
        return self.actions(ctx) if rel_folder == "" else []


class ReactNative(Provider):
    id, title, priority, icon = "react-native", "React Native", 44, ("RN", "#61DAFB")
    markers = ("package.json",)

    def detect(self, folder, project):
        return has_dep(folder, "react-native") and not has_dep(folder, "expo")

    def actions(self, ctx):
        return [Action("start", "Start Metro", lambda c: run_script_or(c, "start", ["npx", "react-native", "start"]),
                       toolbar=True, opens="none", icon="SP_MediaPlay"),
                Action("android", "Run on Android", lambda c: run_script_or(c, "android",
                                                                           ["npx", "react-native", "run-android"]),
                       opens="none"),
                Action("ios", "Run on iOS", lambda c: run_script_or(c, "ios", ["npx", "react-native", "run-ios"]),
                       opens="none"),
                Separator(),
                Action("doctor", "react-native doctor", lambda c: c.run_cli(["npx", "react-native", "doctor"]),
                       opens="none"),
                Action("clean-android", "Clean Android Build",
                       lambda c: c.run_cli([str(c.path("android/gradlew.bat" if os.name == "nt" else "android/gradlew")),
                                            "clean"], cwd=c.path("android")), opens="none",
                       enabled=lambda c: c.path("android").is_dir())]


PROVIDERS = [NodeScriptsPlus(), NestJS(), Angular(),
             ViteApp("react", "React", ("Re", "#149ECA"), "react"),
             ViteApp("vue", "Vue", ("Vu", "#42B883"), "vue"),
             ViteApp("svelte", "Svelte", ("Sv", "#FF3E00"), "svelte"),
             Express(), Expo(), ReactNative()]
