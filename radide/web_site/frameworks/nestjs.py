"""NestJS web sites (``nestjs-web`` plugin) - TypeScript on Node.js.

- **New Project**: "NestJS App" writes a small Nest 11 project (module, controller, service, a products resource;
  ``npm install`` runs on the first start), "NestJS (nest new)" runs the official CLI
  ``npx @nestjs/cli new --skip-install`` (needs the network).
- **Run (Ctrl+F5)**: ``nest start --watch`` (= ``npm run start:dev``) with ``PORT`` set, behind the DevServer -
  Nest recompiles and restarts by itself.
- **Debug (F5)**: the site is a ``node`` site for radide/web_site/debug.py: the server then runs as
  ``node --inspect-wait -r ts-node/register -r tsconfig-paths/register src/main.ts`` (transpile-only) and
  **vscode-js-debug** attaches - breakpoints in the .ts files; the IDE restarts it when a .ts file changes.
- **Routes** from ``@Controller('x')`` + ``@Get(':id')``... (and ``app.setGlobalPrefix``), **CLI panel**:
  ``nest g controller|service|module|resource``, npm scripts. TypeScript IntelliSense comes from
  typescript-language-server (radide/lsp.py).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..project import SiteTemplate, register_template
from .backend_common import (FrameworkPlugin, Route, Tool, filter_prefix, join_url, line_of, read_text,
                             reporter_cancelled, reporter_log, run, string_context, walk_files, which, with_progress,
                             write_files)

DECORATOR_RE = re.compile(r"@(Get|Post|Put|Patch|Delete|All|Options|Head)\s*\(\s*(?:['\"`]([^'\"`]*)['\"`])?")
CONTROLLER_RE = re.compile(r"@Controller\s*\(\s*(?:['\"`]([^'\"`]*)['\"`]|\{[^}]*path\s*:\s*['\"`]([^'\"`]*)['\"`])?")


def node_exe() -> str:
    return which("node") or (r"C:\Program Files\nodejs\node.exe" if Path(r"C:\Program Files\nodejs\node.exe").exists()
                             else "")


def npm_exe() -> str:
    return which("npm.cmd", "npm")


def npx_exe() -> str:
    return which("npx.cmd", "npx")


def nest_cli(folder: Path) -> str:
    p = Path(folder) / "node_modules" / "@nestjs" / "cli" / "bin" / "nest.js"
    return str(p) if p.exists() else ""


# ============================================================================ templates
def _files(name: str) -> dict[str, str]:
    pkg = re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-") or "nest-app"
    return {
        "package.json": json.dumps({
            "name": pkg, "version": "0.0.1", "private": True, "license": "UNLICENSED",
            "scripts": {"build": "nest build", "start": "nest start", "start:dev": "nest start --watch",
                        "start:debug": "nest start --debug --watch", "start:prod": "node dist/main"},
            "dependencies": {"@nestjs/common": "^11.0.1", "@nestjs/core": "^11.0.1",
                             "@nestjs/platform-express": "^11.0.1", "reflect-metadata": "^0.2.2", "rxjs": "^7.8.1"},
            "devDependencies": {"@nestjs/cli": "^11.0.0", "@nestjs/schematics": "^11.0.0",
                                "@types/express": "^5.0.0", "@types/node": "^24.0.0", "source-map-support": "^0.5.21",
                                "ts-node": "^10.9.2", "tsconfig-paths": "^4.2.0", "typescript": "^5.7.3"}},
            indent=2) + "\n",
        "nest-cli.json": json.dumps({"$schema": "https://json.schemastore.org/nest-cli", "collection": "@nestjs/schematics",
                                     "sourceRoot": "src", "compilerOptions": {"deleteOutDir": True}}, indent=2) + "\n",
        "tsconfig.json": json.dumps({"compilerOptions": {
            "module": "commonjs", "declaration": True, "removeComments": True, "emitDecoratorMetadata": True,
            "experimentalDecorators": True, "allowSyntheticDefaultImports": True, "target": "ES2023",
            "sourceMap": True, "outDir": "./dist", "baseUrl": "./", "incremental": True, "skipLibCheck": True,
            "strictNullChecks": True, "forceConsistentCasingInFileNames": True, "noImplicitAny": False,
            "strictBindCallApply": False, "noFallthroughCasesInSwitch": False}}, indent=2) + "\n",
        "tsconfig.build.json": json.dumps({"extends": "./tsconfig.json",
                                           "exclude": ["node_modules", "test", "dist", "**/*spec.ts"]}, indent=2) + "\n",
        "src/main.ts": """import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(process.env.PORT ?? 3000, '127.0.0.1');
  console.log(`Application is running on: ${await app.getUrl()}`);
}
bootstrap();
""",
        "src/app.module.ts": """import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { ProductsModule } from './products/products.module';

@Module({
  imports: [ProductsModule],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
""",
        "src/app.controller.ts": f"""import {{ Controller, Get, Header }} from '@nestjs/common';
import {{ AppService }} from './app.service';

@Controller()
export class AppController {{
  constructor(private readonly appService: AppService) {{}}

  @Get()
  @Header('Content-Type', 'text/html; charset=utf-8')
  home(): string {{
    return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>{name}</title>
<style>body{{font-family:"Segoe UI",sans-serif;margin:40px;background:#f5f6f8}}h1{{color:#e0234e}}</style></head>
<body><h1>{name}</h1><p>${{this.appService.getHello()}}</p>
<p><a href="/products">/products</a> (JSON) - <a href="/health">/health</a></p></body></html>`;
  }}

  @Get('health')
  health() {{
    return {{ status: 'ok', time: new Date().toISOString() }};
  }}
}}
""",
        "src/app.service.ts": f"""import {{ Injectable }} from '@nestjs/common';

@Injectable()
export class AppService {{
  getHello(): string {{
    return 'Hello from {name} - a NestJS app made with RAD IDE!';
  }}
}}
""",
        "src/products/products.module.ts": """import { Module } from '@nestjs/common';
import { ProductsController } from './products.controller';
import { ProductsService } from './products.service';

@Module({
  controllers: [ProductsController],
  providers: [ProductsService],
})
export class ProductsModule {}
""",
        "src/products/products.service.ts": """import { Injectable, NotFoundException } from '@nestjs/common';

export interface Product { id: number; name: string; price: number; }

@Injectable()
export class ProductsService {
  private readonly products: Product[] = [
    { id: 1, name: 'Keyboard', price: 25 },
    { id: 2, name: 'Mouse', price: 12.5 },
  ];

  findAll(): Product[] {
    return this.products;
  }

  findOne(id: number): Product {
    const p = this.products.find((x) => x.id === id);
    if (!p) throw new NotFoundException(`Product ${id} not found`);
    return p;
  }

  create(data: Omit<Product, 'id'>): Product {
    const p = { id: this.products.length + 1, ...data };
    this.products.push(p);
    return p;
  }
}
""",
        "src/products/products.controller.ts": """import { Body, Controller, Get, Param, ParseIntPipe, Post } from '@nestjs/common';
import { Product, ProductsService } from './products.service';

@Controller('products')
export class ProductsController {
  constructor(private readonly products: ProductsService) {}

  @Get()
  findAll(): Product[] {
    return this.products.findAll();
  }

  @Get(':id')
  findOne(@Param('id', ParseIntPipe) id: number): Product {
    return this.products.findOne(id);
  }

  @Post()
  create(@Body() body: { name: string; price: number }): Product {
    return this.products.create({ name: body.name, price: Number(body.price) || 0 });
  }
}
""",
        ".gitignore": "node_modules/\ndist/\n",
    }


def _create_builtin(folder: Path, name: str) -> dict:
    write_files(folder, _files(name))
    return {"start": "src/main.ts"}     # no "framework" key: debug.start treats that as a Vite-style app


def _create_cli(folder: Path, name: str) -> dict:
    npx = npx_exe()
    if npx:
        argv = [npx, "--yes", "@nestjs/cli@11", "new", re.sub(r"[^A-Za-z0-9-]", "-", name).lower(),
                "--directory", ".", "--skip-install", "--skip-git", "--package-manager", "npm"]
        code, _out = with_progress("Creating the project (nest new)",
                                   lambda r: run(argv, cwd=folder, timeout=600, log=reporter_log(r),
                                                 cancelled=reporter_cancelled(r)), cancellable=True)
        if code == 0 and (Path(folder) / "src" / "main.ts").exists():
            return {"start": "src/main.ts"}     # no "framework" key: debug.start treats that as a Vite-style app
    return _create_builtin(folder, name)


register_template(SiteTemplate("nestjs-app", "NestJS App", "A NestJS 11 application (TypeScript): app module, "
                               "controller, service and a products REST resource. npm install runs on the first start.",
                               ("nestjs-web",), _create_builtin, 10, extra={"framework": "nestjs"}))
register_template(SiteTemplate("nestjs-cli", "NestJS (nest new)", "The official starter made by the Nest CLI "
                               "(npx @nestjs/cli new - downloads the CLI, needs the network).",
                               ("nestjs-web",), _create_cli, 20, extra={"framework": "nestjs"}))


# ============================================================================ routes
def nest_routes(folder: Path) -> list[Route]:
    folder = Path(folder)
    src = folder / "src"
    prefix = ""
    m = re.search(r"setGlobalPrefix\s*\(\s*['\"`]([^'\"`]*)", read_text(src / "main.ts"))
    if m:
        prefix = m.group(1)
    out: list[Route] = []
    for f in walk_files(src if src.is_dir() else folder, (".ts",), 4000):
        if f.name.endswith((".spec.ts", ".d.ts")):
            continue
        text = read_text(f)
        cm = CONTROLLER_RE.search(text)
        if not cm:
            continue
        base = cm.group(1) or cm.group(2) or ""
        cls = re.search(r"class\s+(\w+)", text[cm.end():])
        cname = cls.group(1) if cls else f.stem
        for dm in DECORATOR_RE.finditer(text, cm.end()):
            after = re.sub(r"@\w+\s*\([^)]*\)", "", text[dm.end():dm.end() + 300])
            mm = re.search(r"(?:async\s+)?(\w+)\s*\(", after)
            handler = f"{cname}.{mm.group(1)}" if mm else cname
            path = join_url(prefix, base, dm.group(2) or "")
            out.append(Route(dm.group(1).upper().replace("ALL", "ANY"), path, handler, str(f),
                             line_of(text, dm.start()), mm.group(1) if mm else ""))
    return sorted(out, key=lambda r: (r.path, r.method))


# ============================================================================ plugin
class NestPlugin(FrameworkPlugin):
    id = "nestjs-web"
    display_name = "NestJS Web App (TypeScript)"
    framework = "nestjs"
    framework_title = "NestJS"
    cli_title = "Nest CLI / npm"
    code_ext = ".ts"
    web_kind = "node"              # radide/web_site/debug.py: node --inspect + js-debug
    default_template = "nestjs-app"
    interpreter_names = ["node"]
    interpreter_hints = [r"C:\Program Files\nodejs\node.exe"]
    tool_names = ["node"]
    install_hint = "Install Node.js (https://nodejs.org)."
    keywords = ("abstract any as async await boolean break case catch class const constructor continue declare "
                "default delete do else enum export extends false finally for from function if implements import in "
                "instanceof interface let module namespace new null number private protected public readonly "
                "return static string super switch this throw true try type typeof undefined var void while yield").split()
    builtins = ["Controller", "Get", "Post", "Put", "Patch", "Delete", "Body", "Param", "Query", "Injectable",
                "Module", "NestFactory", "HttpException", "NotFoundException", "console", "process"]
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"', "'", "`"]

    def find_interpreter(self, configured: str = "") -> str:
        if configured and Path(configured).exists():
            return configured
        return node_exe()

    def module_template(self, name: str) -> str:
        return f"// {name}.ts\nexport {{}};\n"

    def backend(self, server) -> dict:
        node = server.interpreter or node_exe() or "node"
        folder = server.folder
        prepare = []
        if not (folder / "node_modules").is_dir():
            prepare.append([npm_exe() or "npm", "install", "--no-audit", "--no-fund"])
        env = {"PORT": "{port}", "NODE_ENV": "development"}
        main = str(server.config.get("start") or "src/main.ts")
        if not main.endswith(".ts"):
            main = "src/main.ts"
        if callable(getattr(server, "backend_hook", None)) or server.config.get("run_mode") == "ts-node":
            # debug run: one node process running the TypeScript sources (js-debug maps the breakpoints)
            env.update({"TS_NODE_TRANSPILE_ONLY": "true", "TS_NODE_PROJECT": "tsconfig.json"})
            return {"argv": [node, "-r", "ts-node/register", "-r", "tsconfig-paths/register", main], "cwd": folder,
                    "env": env, "prepare": prepare, "restart_on_change": True, "timeout": 120}
        cli = str(folder / "node_modules" / "@nestjs" / "cli" / "bin" / "nest.js")
        return {"argv": [node, cli, "start", "--watch", "--preserveWatchOutput"], "cwd": folder, "env": env,
                "prepare": prepare, "restart_on_change": False, "timeout": 180}

    # ---- tools
    def tool_status(self) -> list[Tool]:
        try:
            from ...lsp import server_command
            ts = " ".join(server_command("typescript") or [])
        except Exception:  # noqa: BLE001
            ts = ""
        return [Tool("Node.js", node_exe(), "run", self.install_hint), Tool("npm", npm_exe(), "packages", ""),
                Tool("typescript-language-server", ts, "TypeScript IntelliSense (LSP)",
                     "Tools > Install Web Language Servers")]

    # ---- CLI
    def cli_presets(self, project) -> list[tuple[str, str]]:
        return [("Generate controller", "nest g controller {name}"),
                ("Generate service", "nest g service {name}"),
                ("Generate module", "nest g module {name}"),
                ("Generate REST resource (CRUD)", "nest g resource {name} --type rest --crud"),
                ("Generate guard", "nest g guard {name}"),
                ("Install packages", "npm install"), ("Add package", "npm install {name}"),
                ("Build", "npm run build"), ("Run tests", "npm test"), ("Lint", "npm run lint"),
                ("Nest info", "nest info")]

    def cli_env(self, project) -> dict:
        return {"NO_COLOR": "1", "FORCE_COLOR": "0"}

    def cli_argv(self, project, command: str) -> list[str]:
        argv = super().cli_argv(project, command)
        if not argv:
            return argv
        folder = Path(project.folder)
        head = argv[0].lower()
        if head == "nest":
            cli = nest_cli(folder)
            if cli:
                return [node_exe() or "node", cli, *argv[1:]]
            return [npx_exe() or "npx", "--yes", "@nestjs/cli@11", *argv[1:]]
        if head in ("npm", "npx"):
            argv[0] = (npm_exe() if head == "npm" else npx_exe()) or head
        return argv

    # ---- routes
    def routes(self, project) -> list[Route]:
        return nest_routes(Path(project.folder))

    def view_names(self, project) -> list[str]:
        views = Path(project.folder) / "views"
        return sorted(f.stem for f in views.glob("*.*")) if views.is_dir() else []

    def completion_items(self, project, path: Path, before: str):
        if Path(path).suffix.lower() not in (".ts", ".html", ".hbs", ".js"):
            return None
        ctx = string_context(before)
        if ctx is None:
            return None
        head, prefix = ctx
        if re.search(r"@Render\s*\(\s*$", head):
            return filter_prefix([(v, "file", "view") for v in self.view_names(project)], prefix)
        if re.search(r"(?:href|action|src)\s*=\s*$|fetch\(\s*$|\.get\(\s*$|redirect\(\s*$|@Redirect\(\s*$", head):
            return filter_prefix([(r.url_path(), "value", f"{r.method} {r.handler}") for r in self.routes(project)],
                                 prefix)
        return None


PLUGIN = NestPlugin()

__all__ = ["NestPlugin", "PLUGIN", "nest_cli", "nest_routes"]
